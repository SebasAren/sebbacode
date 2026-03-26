"""Rich live display for agent execution progress."""

import logging
import re
import time
from collections import deque

from langchain_core.messages import AIMessage, ToolMessage
from rich.console import Console, Group
from rich.live import Live
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

STATUS_STYLES = {
    "done": ("\u2713", "green"),
    "running": ("\u25b6", "yellow bold"),
    "pending": ("\u00b7", "dim"),
    "blocked": ("\u2717", "red"),
}

# Node name -> phase label for the header
PHASE_MAP = {
    "load_context": "Loading context",
    "explore_bootstrap": "Exploring codebase",
    "plan_recon": "Reconnoitering codebase",
    "plan_draft": "Planning",
    "plan_critique": "Validating plan",
    "plan_refine": "Refining plan",
    "build_dag": "Building task DAG",
    "human_approval": "Awaiting approval",
    "dispatch_tasks": "Dispatching tasks",
    "collect_results": "Collecting results",
    "extract_session": "Extracting session",
    "summarize_to_l1": "Summarizing memories",
}

# Worker subgraph node -> activity label
WORKER_PHASE_MAP = {
    "recon": "Reconnaissance",
    "match_rules": "Loading rules",
    "deepen_context": "Loading context",
    "llm_call": "Thinking",
    "tools": "Running tools",
    "summarize": "Summarizing",
    "extract_memory": "Extracting memory",
}

# Tool name -> human-readable action verb
TOOL_LABELS = {
    "read_file": "Reading",
    "write_file": "Writing",
    "run_command": "Running",
    "search_code": "Searching",
    "search_files": "Finding",
    "list_directory": "Listing",
    "mark_task_done": "Completed task",
    "signal_blocked": "Blocked",
    "add_subtask": "Adding subtask",
}


def _format_tool_call_concise(name: str, args: dict) -> str:
    """Format a tool call for normal (non-verbose) display."""
    label = TOOL_LABELS.get(name, name)
    if name == "read_file":
        return f"{label} {args.get('path', '?')}"
    if name == "write_file":
        return f"{label} {args.get('path', '?')}"
    if name == "run_command":
        cmd = args.get("command", "?")
        if len(cmd) > 60:
            cmd = cmd[:57] + "..."
        return f"{label}: {cmd}"
    if name in ("search_code", "search_files"):
        q = args.get("query") or args.get("pattern", "?")
        return f"{label}: {q}"
    if name == "mark_task_done":
        return "Task complete"
    if name == "signal_blocked":
        return f"Blocked: {args.get('reason', '?')}"
    if name == "add_subtask":
        return f"Adding subtask: {args.get('description', '?')[:50]}"
    # Generic fallback
    arg_str = ", ".join(f"{k}={repr(v)[:30]}" for k, v in list(args.items())[:3])
    return f"{name}({arg_str})"


def _format_tool_call_verbose(name: str, args: dict) -> str:
    """Format a tool call for verbose display."""
    arg_str = ", ".join(f"{k}={repr(v)[:60]}" for k, v in args.items())
    return f"{name}({arg_str})"


class RichDisplay:
    """Manages a Rich Live display for agent execution progress."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.start_time = time.monotonic()
        self.phase = "Initializing"
        self.tasks: dict[str, dict] = {}
        self.activity: deque[str] = deque(maxlen=20)
        self.ns_to_task: dict[tuple, str] = {}
        self.console = Console()
        self.live: Live | None = None
        self._is_terminal = self.console.is_terminal
        self._last_update = 0.0
        self._saved_handlers: list = []

    def __enter__(self):
        if self._is_terminal:
            self.live = Live(
                self._render(),
                console=self.console,
                refresh_per_second=4,
                transient=True,
            )
            self.live.__enter__()
            # Redirect logging through Rich so it doesn't clobber the Live display
            root = logging.getLogger()
            self._saved_handlers = root.handlers[:]
            root.handlers.clear()
            root.addHandler(RichHandler(console=self.console, show_path=False))
        return self

    def __exit__(self, *args):
        if self.live:
            self.live.__exit__(*args)
            self.live = None
            # Restore original logging handlers
            root = logging.getLogger()
            root.handlers.clear()
            root.handlers.extend(self._saved_handlers)
            self._saved_handlers.clear()
        # Print final state so it persists in terminal
        if self._is_terminal:
            self.console.print(self._render())

    def pause(self):
        """Stop the live display for interactive input."""
        if self.live:
            self.live.stop()

    def resume(self):
        """Restart the live display after interactive input."""
        if self.live:
            self.live.start()

    def set_phase(self, phase: str):
        self.phase = phase
        if not self._is_terminal:
            elapsed = time.monotonic() - self.start_time
            self.console.print(f"[{elapsed:.1f}s] {phase}")

    def log_activity(self, task_id: str | None, message: str):
        prefix = f"[{task_id[:8]}] " if task_id else ""
        self.activity.append(f"{prefix}{message}")
        if not self._is_terminal and self.verbose:
            self.console.print(f"  {prefix}{message}")

    def update_tasks(self, tasks: dict):
        self.tasks = tasks

    def handle_stream_event(self, chunk: tuple):
        """Process a v1 stream chunk: (namespace, mode, payload)."""
        ns, mode, payload = chunk

        if mode == "updates":
            self._handle_update(ns, payload)
        elif mode == "messages":
            self._handle_message(ns, payload)

        # Throttle live.update() to avoid flickering from per-token updates
        if self.live:
            now = time.monotonic()
            if now - self._last_update >= 0.25:
                self.live.update(self._render())
                self._last_update = now

    def _handle_update(self, ns: tuple, data: dict):
        """Handle a node update event."""
        if not ns:
            # Parent graph node
            for node_name, output in data.items():
                phase = PHASE_MAP.get(node_name)
                if phase and phase != self.phase:
                    self.set_phase(phase)
                if node_name in ("build_dag", "dispatch_tasks", "collect_results"):
                    tasks = output.get("tasks")
                    if tasks:
                        self.update_tasks(tasks)
        else:
            # Subgraph event — try to identify task
            task_id = self._resolve_task_id(ns, data)
            for node_name, output in data.items():
                label = WORKER_PHASE_MAP.get(node_name)
                if label:
                    self.log_activity(task_id, f"{label}...")

    def _handle_message(self, ns: tuple, data: tuple):
        """Handle a message event: (message, metadata)."""
        message, metadata = data
        task_id = self._resolve_task_id(ns)

        if isinstance(message, AIMessage):
            if message.tool_calls:
                for tc in message.tool_calls:
                    name = tc["name"]
                    args = tc.get("args", {})
                    if self.verbose:
                        line = _format_tool_call_verbose(name, args)
                    else:
                        line = _format_tool_call_concise(name, args)
                    self.log_activity(task_id, line)
            elif self.verbose and message.content:
                text = str(message.content).strip()
                # Skip structured output (JSON, markdown tables)
                if text.startswith(("```", "{", "[")):
                    pass
                else:
                    text = re.sub(r"[*`#|]", "", text)
                    text = text.replace("\n", " ")[:80].strip()
                    if text:
                        self.log_activity(task_id, f"LLM: {text}")

        elif isinstance(message, ToolMessage) and self.verbose:
            result = str(message.content).strip().replace("\n", " ")[:80]
            self.log_activity(task_id, f"  \u2192 {message.name}: {result}")

    def _resolve_task_id(self, ns: tuple, data: dict | None = None) -> str | None:
        """Map a namespace tuple to a task ID."""
        if not ns:
            return None

        # Check cache
        if ns in self.ns_to_task:
            return self.ns_to_task[ns]

        # Also check parent namespaces (nested subgraphs like llm_loop inside task_worker)
        for i in range(len(ns), 0, -1):
            prefix = ns[:i]
            if prefix in self.ns_to_task:
                self.ns_to_task[ns] = self.ns_to_task[prefix]
                return self.ns_to_task[prefix]

        # Try to extract task ID from update data
        if data:
            for _node_name, output in data.items():
                if isinstance(output, dict):
                    task = output.get("task")
                    if isinstance(task, dict) and "id" in task:
                        self.ns_to_task[ns] = task["id"]
                        return task["id"]

        # Fallback: extract from namespace string (e.g. "task_worker:task-1")
        for part in ns:
            if "task_worker" in part and ":" in part:
                tid = part.split(":", 1)[1]
                self.ns_to_task[ns] = tid
                return tid

        return "worker"

    def _render(self):
        """Build the Rich renderable from current state."""
        elapsed = time.monotonic() - self.start_time
        header = Text(f" {self.phase}", style="bold cyan")
        header.append(f"  [{elapsed:.1f}s]", style="dim")

        parts = [header]

        # Task table
        if self.tasks:
            table = Table(show_header=False, padding=(0, 1), expand=True)
            table.add_column("s", width=2, no_wrap=True)
            table.add_column("id", style="bold", width=12, no_wrap=True)
            table.add_column("desc")
            for tid, task in self.tasks.items():
                icon, style = STATUS_STYLES.get(task["status"], ("?", ""))
                table.add_row(icon, tid, task["description"], style=style)
            parts.append(Panel(table, title="Tasks", border_style="blue", padding=(0, 1)))

        # Activity log
        if self.activity:
            activity_text = "\n".join(self.activity)
            parts.append(Panel(activity_text, title="Activity", border_style="dim", padding=(0, 1)))

        return Group(*parts)

    def show_plan(self, tasks: dict):
        """Render the plan for approval (outside Live context)."""
        table = Table(title="Execution Plan", expand=True, padding=(0, 1))
        table.add_column("Task", style="bold", no_wrap=True)
        table.add_column("Description")
        table.add_column("Dependencies", style="dim")
        table.add_column("Files", style="dim")
        for tid, task in tasks.items():
            deps = ", ".join(task["depends_on"]) or "-"
            files = ", ".join(task["target_files"]) or "-"
            table.add_row(tid, task["description"], deps, files)
        self.console.print(table)

    def show_final_report(self, completed: list[str], elapsed: float):
        """Print the final completion summary."""
        if completed:
            self.console.print(
                f"\n[bold green]\u2713[/] Completed {len(completed)} tasks in {elapsed:.1f}s:"
            )
            for tid in completed:
                self.console.print(f"  - {tid}")
        else:
            self.console.print("\n[yellow]No tasks completed this session.[/]")
