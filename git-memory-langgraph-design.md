# Git-Native Agent Memory for LangGraph

A LangGraph coding agent where all context lives as Markdown in the git repo.
The GCC roadmap drives execution, GCC commits are the session log that feeds
memory extraction, GCC branches are real code exploration using git worktrees,
and an explorer agent grounds everything in the actual codebase.

**Influences**: GCC paper (commit/branch/merge context protocol), OpenViking
(tiered L0/L1/L2 loading, session-based extraction), Claude Code (path-scoped
rules, `.claude/rules/`), Beads (git-native task tracking).

---

## 1. Repo Directory Structure

```
your-mono-repo/
├── apps/
│   ├── api/
│   │   ├── src/
│   │   └── .agent/rules/              # Per-app rules
│   │           └── api-patterns.md
│   ├── frontend/
│   │   ├── src/
│   │   └── .agent/rules/
│   │           └── react-patterns.md
│   └── worker/
│       ├── src/
│       └── .agent/rules/
│               └── queue-patterns.md
├── packages/
│   └── shared-lib/
├── .agent/                            # Root agent directory
│   ├── memory/
│   │   ├── _index.md                  # L0: one-line summaries (always loaded)
│   │   ├── architecture.md            # L1: architectural overview
│   │   ├── architecture/              # L2: deep detail per domain
│   │   │   ├── auth-system.md
│   │   │   ├── ci-pipeline.md
│   │   │   └── database-patterns.md
│   │   ├── conventions.md             # L1: coding conventions overview
│   │   ├── conventions/               # L2: detailed conventions
│   │   │   ├── error-handling.md
│   │   │   ├── testing.md
│   │   │   └── logging.md
│   │   └── decisions/
│   │       ├── _index.md              # L0: decision log summaries
│   │       ├── 2026-03-20-switch-to-pnpm.md
│   │       └── 2026-03-25-adopt-zod.md
│   ├── sessions/
│   │   └── 2026-03-25.md             # Daily session summaries
│   ├── rules/
│   │   ├── global.md                  # Always loaded (no path scope)
│   │   ├── typescript.md              # Scoped to **/*.ts
│   │   ├── testing.md                 # Scoped to **/*.test.*, **/*.spec.*
│   │   ├── ci.md                      # Scoped to .gitlab-ci.yml, **/Dockerfile
│   │   └── kubernetes.md              # Scoped to **/k8s/**, **/helm/**
│   ├── gcc/
│   │   ├── main.md                    # Roadmap = task backlog
│   │   ├── commits/                   # Session log = extraction input
│   │   │   ├── 001.md
│   │   │   └── 002.md
│   │   └── branches/                  # Exploration records
│   │       └── explore-143022-cookies/
│   │           ├── context.md
│   │           └── commits/
│   │               └── 001.md
│   └── config.yaml
└── .gitignore                         # Includes: .agent/worktrees/
```

---

## 2. Three Layers: Memory, Rules, GCC

### Memory (`memory/`) — What the Agent Knows

Facts about the codebase, architecture, conventions, past decisions.
Loaded by **relevance** (LLM reads the index and picks what's useful).
Persists long-term across roadmaps.

### Rules (`rules/`) — How the Agent Must Behave

Imperative instructions scoped to file paths. Loaded by **path matching**
against the files the agent is working with. High priority in the prompt.
Persists long-term, grows as the agent discovers patterns.

### GCC (`gcc/`) — What the Agent Is Doing

The roadmap (task backlog), progress commits (session log), and
exploration branches. Loaded **always** (roadmap) or by **recency**
(K=1 latest commit). Lifespan is per-roadmap — archived on completion.

| Layer   | Contains              | Loaded by        | Lifespan     |
|---------|-----------------------|------------------|--------------|
| Memory  | Facts, architecture   | Relevance (LLM)  | Long-term    |
| Rules   | Behaviour imperatives | Path matching     | Long-term    |
| GCC     | Goals, progress, exploration | Always / K=1 | Per-roadmap |

---

## 3. Tiered Loading (OpenViking-inspired)

### L0 — Always Loaded (< 500 tokens)

`_index.md` files. Loaded into every prompt. The agent's table of contents.

```markdown
<!-- .agent/memory/_index.md -->
# Agent Memory Index

- **architecture**: Mono repo, 3 apps (api, frontend, worker), pnpm workspaces, K8s deploy
- **conventions**: Strict TypeScript, Zod validation, structured logging, vitest
- **decisions**: 12 active decisions (latest: adopt Zod for all validation, 2026-03-25)
- **auth**: JWT + refresh tokens, middleware-based, shared package
- **ci**: GitLab CI, conventional commits, Release Please, per-app SemVer
```

### L1 — Loaded on Relevance (< 2000 tokens each)

Top-level `.md` files (e.g. `architecture.md`, `conventions.md`).
The agent reads L0 + the current todo, decides which L1 files matter.

### L2 — Loaded on Demand (unbounded)

Subdirectory files (e.g. `architecture/auth-system.md`). Only loaded
when the agent specifically needs deep detail on a topic.

---

## 4. Path-Scoped Rules (Claude Code-inspired)

### Format

```yaml
# .agent/rules/testing.md
---
paths:
  - "**/*.test.ts"
  - "**/*.spec.ts"
  - "**/__tests__/**"
---
# Testing Rules

- Use vitest, not jest
- Every test file must have a describe block matching the module name
- Use factory functions for test data, never inline objects
- Integration tests go in __tests__/integration/
- Mock external services, never databases (use testcontainers)
```

### Per-App Rules

```yaml
# apps/api/.agent/rules/api-patterns.md
---
paths:
  - "apps/api/**"
---
# API Application Rules

- All endpoints use Zod schemas for request/response validation
- Error responses follow RFC 7807 Problem Details format
- Route handlers are thin — business logic lives in services/
- Use drizzle ORM, never raw SQL
```

Rules without `paths:` frontmatter are global — always loaded.
Rules with `paths:` only load when the agent's target files match.

---

## 5. GCC Roadmap as Task Driver

### The Core Idea

`main.md` is the agent's task backlog. The agent doesn't receive a
separate "task" — it reads the roadmap, picks the next unchecked todo,
and works on it. Progress is tracked in the same file.

### Roadmap Format

```markdown
<!-- .agent/gcc/main.md -->
# Implement User Authentication

## Goal
Add JWT-based authentication to the API app with refresh token rotation.

## Context
Triggered by GitLab Issue #142. The API currently has no auth.
Public endpoints must remain accessible without tokens.

## Todos
- [x] Research JWT vs session approach → chose JWT (branch: jwt-vs-session, merged)
- [x] Create auth middleware with token validation
- [ ] Add login/register endpoints with Zod schemas
- [ ] Integrate refresh token rotation
- [ ] Add auth tests (unit + integration)
- [ ] Update API documentation

## Target Files
- apps/api/src/middleware/auth.ts
- apps/api/src/routes/auth/
- apps/api/src/services/auth.service.ts
- packages/shared-lib/src/tokens.ts

## Active Branches
None currently.

## Decisions Made
- JWT over sessions: stateless, better for K8s horizontal scaling
- Refresh tokens stored in httpOnly cookies, not localStorage
- Token signing uses shared-lib so worker app can validate too

## Constraints
- Must use shared-lib for token signing
- Must not break existing public endpoints
- Error responses must follow RFC 7807
```

### Seeding from GitLab Issues

```python
def seed_roadmap_from_issue(issue_id: int) -> None:
    """Fetch a GitLab issue and generate initial main.md."""
    issue = gitlab_client.issues.get(issue_id)

    seed_prompt = f"""Decompose this GitLab issue into an agent roadmap.

Issue #{issue.iid}: {issue.title}
{issue.description}

Labels: {issue.labels}
Milestone: {issue.milestone}

Generate a main.md with these sections:
- Goal: one paragraph
- Context: where this came from, current state of the codebase
- Todos: ordered, actionable steps (each completable in one session)
- Target Files: best guess at files to create or modify
- Active Branches: (start empty)
- Decisions Made: (start empty)
- Constraints: non-functional requirements, things to preserve

Keep todos concrete and specific.
"""

    response = llm.invoke(seed_prompt)

    gcc_dir = Path(".agent/gcc")
    gcc_dir.mkdir(parents=True, exist_ok=True)
    (gcc_dir / "main.md").write_text(response.content)
    (gcc_dir / "commits").mkdir(exist_ok=True)
    (gcc_dir / "branches").mkdir(exist_ok=True)
```

### Roadmap Size Control

`main.md` represents ONE active task. When completed:
1. Final state archived as a summary commit in `commits/`
2. Learnings extracted into `memory/` by `extract_session`
3. `main.md` cleared or replaced with the next seeded roadmap

---

## 6. GCC Commits as Session Log

### How It Works

During execution, the agent calls `gcc_commit` to log structured
progress. These commit files are the PRIMARY INPUT to `extract_session`,
which distills them into lasting memory updates.

### Commit Format

```markdown
# Commit 003: Created auth middleware

**Date**: 2026-03-25T14:30:00
**Todo**: Create auth middleware with token validation

## What I Did
- Created apps/api/src/middleware/auth.ts
- Added verifyToken import from shared-lib
- Registered middleware in app.ts for /api/* routes
- Excluded /api/health and /api/docs from auth

## Decisions Made
- Cookie extraction over Authorization header (httpOnly = more secure)
- Followed existing middleware pattern from logging.ts, not guard pattern

## Issues Encountered
- shared-lib tokens.ts was missing TokenPayload export → added it
- Initial implementation broke /api/health → added exclusion list

## Files Touched
- apps/api/src/middleware/auth.ts (created)
- apps/api/src/app.ts (modified — added middleware registration)
- packages/shared-lib/src/tokens.ts (modified — added export)

## Tests
- Ran existing test suite: all passing
- No new tests yet (separate todo)
```

The structured sections (What I Did, Decisions Made, Issues Encountered,
Files Touched) are the contract between executor and extractor.

### Data Flow

```
execute_todo
  ├── agent works on code
  ├── calls gcc_commit (structured log of what/why/issues)
  ├── optionally calls gcc_explore/evaluate/adopt
  ├── calls mark_todo_done
  │
  ▼
extract_session
  ├── reads .agent/gcc/commits/ written this session
  ├── reads exploration branches if any resolved
  ├── distills into:
  │   ├── memory updates (new facts)
  │   ├── new rules (patterns discovered)
  │   ├── decisions (choices made + alternatives rejected)
  │   └── index updates (L0 summaries)
  ▼
writes to .agent/memory/, .agent/rules/, .agent/memory/decisions/
```

---

## 7. Branch Exploration with Git Worktrees

### When Branches Are Used

Some decisions can't be made by reasoning alone:
- "Should auth use cookies or Authorization headers?"
- "Is argon2 or bcrypt better for our setup?"
- "Class-based or functional service pattern?"

The agent implements both approaches in isolated git worktrees,
evaluates them, and adopts the winner.

### Worktree Layout

```
Main working directory:     ./
Worktree for approach A:    ./.agent/worktrees/explore-143022/cookies/
Worktree for approach B:    ./.agent/worktrees/explore-143022/headers/
```

### Exploration Flow

```
Agent working on todo
        │
        ▼
  "I'm not sure whether to use cookies or headers"
        │
        ▼
  gcc_explore ──► creates worktrees + branch records
        │
  ┌─────┴──────┐
  ▼            ▼
Try A        Try B        Agent implements each (sequentially or subagents)
cookies      headers
  │            │
  ▼            ▼
Test A       Test B       Run tests, check complexity
  │            │
  └─────┬──────┘
        ▼
  gcc_evaluate ──► compare results, pick winner
        │
        ▼
  gcc_adopt ──► merge winner, clean up worktrees, record decision
        │
        ▼
  Agent continues with chosen approach
```

---

## 8. Explorer Agent

### Why Explore?

Without exploration the agent works from assumptions — the roadmap
guesses target files, memory might be stale, the current code state
is unknown. The explorer grounds everything in the actual codebase.

### Three Modes

#### Bootstrap (first run / empty memory)

Scans the entire repo to build initial memory. Reads package.json,
tsconfig, CI configs, READMEs. Generates `_index.md`, `architecture.md`,
conventions, and infers rules from linter configs.

#### Validate (start of new roadmap)

Checks the seeded roadmap against reality. Verifies target files
exist, reads them, traces imports, discovers missing dependencies,
adds constraints. Corrects the roadmap before execution begins.

#### Recon (before each todo)

Lightweight per-todo briefing. Reads the specific files, traces one
level of imports, checks for existing tests, looks at recent git
history. Produces a structured briefing for the executor.

### Briefing Format

```markdown
# Briefing: Add login/register endpoints with Zod schemas

## Current State
- apps/api/src/routes/ has 3 existing route modules (users, products, health)
- All use express.Router() with a shared middleware chain
- No auth routes exist yet

## File Analysis
### apps/api/src/routes/auth/ (to be created)
- Directory doesn't exist, will follow pattern from other routes
- Parent routes/index.ts registers all routers — needs updating

### packages/shared-lib/src/tokens.ts (exists)
- Has signToken(), verifyToken(), TokenPayload type
- Uses jsonwebtoken under the hood

## Dependencies Discovered
- apps/api/src/routes/index.ts (needs router registration)
- apps/api/src/db/schema.ts (may need user table changes)

## Existing Tests
- No auth tests yet
- Other routes tested in __tests__/routes/*.route.test.ts

## Recent Git Activity
- auth.ts middleware created 2 commits ago by agent

## Risks
- User table might not have password_hash column
- Need to check if bcrypt/argon2 is already a dependency
```

---

## 9. LangGraph State Schema

```python
from typing import TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentMemoryContext(TypedDict):
    """Assembled memory for this invocation."""
    l0_index: str                      # Always present
    l1_files: dict[str, str]           # filename -> content
    l2_files: dict[str, str]           # filename -> content
    active_rules: dict[str, str]       # rule_name -> content
    session_history: str               # Latest commit from prior session


class TodoItem(TypedDict):
    """A single todo parsed from the roadmap."""
    text: str
    done: bool
    index: int


class AgentState(TypedDict):
    """Main graph state."""
    messages: Annotated[list[BaseMessage], add_messages]

    # Roadmap-driven
    roadmap: str                       # Raw content of main.md
    current_todo: Optional[TodoItem]   # The todo we're working on
    target_files: list[str]            # From roadmap + discovered by explorer

    # Explorer output
    briefing: str                      # Structured codebase briefing
    exploration_mode: str              # "bootstrap" | "validate" | "recon"

    # Memory
    memory: AgentMemoryContext

    # Git/GCC
    working_branch: Optional[str]      # Current git branch
    session_start_commit: int          # Commit count at session start

    # Session tracking
    todos_completed_this_session: list[str]
```

---

## 10. Graph Structure

```
         ┌──────────────────────┐
         │    load_context      │  Read L0 index, detect git branch,
         │                      │  count existing commits
         └──────────┬───────────┘
                    │
                    ▼
              ┌─────┴──────┐
              │ bootstrap?  │  Is memory/_index.md empty or missing?
              ├──yes──┬─no──┤
              ▼       │     │
     explore_bootstrap│     │  Scan entire repo, build initial memory
              │       │     │
              ▼       ▼     │
         ┌──────────────────────┐
         │    read_roadmap      │  Parse main.md, pick next todo,
         │                      │  extract target files
         └──────────┬───────────┘
                    │
                    ▼
              ┌─────┴─────┐
              │ has todo?  │
              ├──yes──┬─no─┤
              │       │    ▼
              │       │  roadmap_done → extract_session → END
              ▼       │
              ┌─────┴──────┐
              │first todo   │  First unchecked todo of this roadmap?
              │of roadmap?  │
              ├──yes──┬─no──┤
              ▼       │     │
     explore_validate │     │  Check roadmap against actual codebase,
              │       │     │  correct target files, add constraints
              ▼       ▼     │
         ┌──────────────────────┐
         │   explore_recon      │  Read target files, trace imports,
         │                      │  check tests, build briefing
         └──────────┬───────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │   match_rules        │  Path-match rules against target files
         └──────────┬───────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │   deepen_context     │  LLM picks relevant L1/L2 memory,
         │                      │  loads latest GCC commit (K=1)
         └──────────┬───────────┘
                    │
                    ▼
         ┌──────────────────────────────────────────────┐
         │                execute_todo                   │
         │                                               │
         │  Code:       read_file, write_file,           │
         │              run_command                       │
         │                                               │
         │  Progress:   gcc_commit (log what you did)    │
         │              mark_todo_done                   │
         │              add_todo                         │
         │              discover_files                   │
         │                                               │
         │  Explore:    gcc_explore (create worktrees)   │
         │              gcc_try_approach (implement)     │
         │              gcc_evaluate (compare & pick)    │
         │              gcc_adopt (apply winner)         │
         │                                               │
         │  Recall:     memory_query                     │
         └──────────────────┬───────────────────────────┘
                            │
                            ▼
         ┌──────────────────────┐
         │   extract_session    │  Read gcc/commits/ from this session,
         │                      │  distill into memory/rules/decisions
         └──────────┬───────────┘
                    │
                    ▼
              ┌─────┴──────┐
              │ continue?  │  More todos + within budget?
              ├──yes──┬─no─┤
              ▼       │    ▼
         read_roadmap │  END
```

---

## 11. Node Implementations

### `load_context`

```python
import subprocess
from pathlib import Path

AGENT_DIR = Path(".agent")


def load_context(state: AgentState) -> dict:
    """Load L0 index and detect git state. Runs once at session start."""

    l0_path = AGENT_DIR / "memory" / "_index.md"
    l0_index = l0_path.read_text() if l0_path.exists() else ""

    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True
    ).stdout.strip()

    # Count existing commits so extract_session knows which are new
    commits_dir = AGENT_DIR / "gcc" / "commits"
    existing_commits = len(list(commits_dir.glob("*.md"))) if commits_dir.exists() else 0

    return {
        "memory": {
            "l0_index": l0_index,
            "l1_files": {},
            "l2_files": {},
            "active_rules": {},
            "session_history": "",
        },
        "working_branch": branch,
        "session_start_commit": existing_commits,
        "todos_completed_this_session": [],
        "briefing": "",
        "exploration_mode": "",
    }


def needs_bootstrap(state: AgentState) -> str:
    """Check if memory needs to be bootstrapped."""
    if not state["memory"]["l0_index"].strip():
        return "yes"
    return "no"
```

### `explore_bootstrap`

```python
def explore_bootstrap(state: AgentState) -> dict:
    """Scan entire repo and build initial memory. Runs once on first use."""

    # Gather repo structure
    tree_output = subprocess.run(
        ["find", ".", "-maxdepth", "3",
         "-not", "-path", "./.git/*",
         "-not", "-path", "*/node_modules/*"],
        capture_output=True, text=True
    ).stdout

    # Read key config files
    config_files = {}
    for pattern in [
        "package.json", "*/package.json", "tsconfig.json", "*/tsconfig.json",
        ".gitlab-ci.yml", "Dockerfile", "*/Dockerfile",
        ".eslintrc*", ".prettierrc*", ".editorconfig",
        "README.md", "CONTRIBUTING.md",
        "vitest.config.*", "jest.config.*",
    ]:
        for f in Path(".").glob(pattern):
            if "node_modules" not in str(f):
                try:
                    config_files[str(f)] = f.read_text()[:2000]
                except Exception:
                    pass

    bootstrap_prompt = f"""You are exploring a codebase for the first time.
Build a complete understanding and generate memory files.

## Directory Structure
{tree_output[:3000]}

## Config Files
{_format_dict(config_files)}

Generate a JSON object:
{{
  "index_md": "Content for _index.md — one-line summaries per area",
  "architecture_md": "Content for architecture.md — L1 system overview",
  "conventions_md": "Content for conventions.md — L1 coding conventions",
  "l2_files": [
    {{"path": "architecture/some-domain.md", "content": "Deep detail"}}
  ],
  "inferred_rules": [
    {{"file": "rules/rule-name.md", "paths": ["glob"] | null, "content": "Rule text"}}
  ]
}}
"""

    response = llm.invoke(bootstrap_prompt)
    result = _parse_json(response.content)

    # Write memory files
    memory_dir = AGENT_DIR / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    (memory_dir / "_index.md").write_text(result["index_md"])
    (memory_dir / "architecture.md").write_text(result["architecture_md"])
    (memory_dir / "conventions.md").write_text(result["conventions_md"])

    for l2 in result.get("l2_files", []):
        path = memory_dir / l2["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(l2["content"])

    (memory_dir / "decisions").mkdir(exist_ok=True)
    (memory_dir / "decisions" / "_index.md").write_text(
        "# Decision Log\nNo decisions recorded yet.\n"
    )

    # Write inferred rules
    for rule in result.get("inferred_rules", []):
        rule_path = AGENT_DIR / rule["file"]
        rule_path.parent.mkdir(parents=True, exist_ok=True)
        content = ""
        if rule.get("paths"):
            content = "---\npaths:\n"
            for p in rule["paths"]:
                content += f'  - "{p}"\n'
            content += "---\n"
        content += rule["content"]
        rule_path.write_text(content)

    return {
        "memory": {**state["memory"], "l0_index": result["index_md"]},
        "exploration_mode": "bootstrap",
    }
```

### `read_roadmap`

```python
import re


def read_roadmap(state: AgentState) -> dict:
    """Parse main.md, extract todos and target files, pick next todo."""
    main_md = AGENT_DIR / "gcc" / "main.md"

    if not main_md.exists():
        return {"roadmap": "", "current_todo": None, "target_files": []}

    roadmap = main_md.read_text()

    # Parse todos
    todos = []
    for i, match in enumerate(re.finditer(r"- \[([ x])\] (.+)", roadmap)):
        todos.append({
            "text": match.group(2).strip(),
            "done": match.group(1) == "x",
            "index": i,
        })

    current_todo = next((t for t in todos if not t["done"]), None)

    # Parse target files section
    target_files = []
    in_targets = False
    for line in roadmap.split("\n"):
        if line.strip().lower().startswith("## target files"):
            in_targets = True
            continue
        if in_targets and line.startswith("##"):
            break
        if in_targets and line.strip().startswith("- "):
            target_files.append(line.strip("- ").strip())

    return {
        "roadmap": roadmap,
        "current_todo": current_todo,
        "target_files": target_files,
    }


def has_todo(state: AgentState) -> str:
    return "no" if state.get("current_todo") is None else "yes"


def is_first_todo(state: AgentState) -> str:
    """Is this the first unchecked todo (fresh roadmap)?"""
    roadmap = state.get("roadmap", "")
    if "- [x]" not in roadmap and state.get("current_todo"):
        return "yes"
    todo = state.get("current_todo")
    if todo and todo["index"] == 0:
        return "yes"
    return "no"
```

### `explore_validate`

```python
def explore_validate(state: AgentState) -> dict:
    """Validate a freshly seeded roadmap against the actual codebase."""
    roadmap = state["roadmap"]
    target_files = state["target_files"]

    # Check which target files exist and read them
    file_status = {}
    for f in target_files:
        path = Path(f)
        if path.exists():
            content = path.read_text()
            file_status[f] = {
                "exists": True,
                "lines": len(content.split("\n")),
                "preview": "\n".join(content.split("\n")[:50]),
            }
        else:
            file_status[f] = {
                "exists": False,
                "parent_exists": path.parent.exists(),
            }

    # Trace imports from existing target files
    imports_found = {}
    for f, status in file_status.items():
        if status.get("exists") and f.endswith((".ts", ".js", ".tsx", ".jsx")):
            result = subprocess.run(
                ["grep", "-n", "^import", f],
                capture_output=True, text=True
            )
            if result.stdout:
                imports_found[f] = result.stdout

    validate_prompt = f"""Validate this roadmap against the actual codebase.

## Roadmap
{roadmap}

## Target File Status
{_format_dict(file_status)}

## Imports Found
{_format_dict(imports_found)}

Produce JSON:
{{
  "corrections": [
    {{"type": "fix_path|add_file|add_todo|add_constraint|refine_todo", "detail": "...", "reason": "..."}}
  ],
  "updated_target_files": ["corrected/list"],
  "warnings": ["things to watch out for"],
  "briefing": "Summary of codebase state relevant to this roadmap"
}}

Only flag real problems, not theoretical ones.
"""

    response = llm.invoke(validate_prompt)
    result = _parse_json(response.content)

    # Apply corrections to main.md
    main_md = AGENT_DIR / "gcc" / "main.md"
    content = main_md.read_text()

    for correction in result.get("corrections", []):
        if correction["type"] == "add_todo":
            content = _append_to_section(content, "## Todos", f"- [ ] {correction['detail']}")
        elif correction["type"] == "add_constraint":
            content = _append_to_section(content, "## Constraints", f"- {correction['detail']}")

    if result.get("updated_target_files"):
        content = _replace_section(
            content, "## Target Files",
            "\n".join(f"- {f}" for f in result["updated_target_files"])
        )

    main_md.write_text(content)

    return {
        "roadmap": main_md.read_text(),
        "target_files": result.get("updated_target_files", target_files),
        "briefing": result.get("briefing", ""),
        "exploration_mode": "validate",
    }
```

### `explore_recon`

```python
def explore_recon(state: AgentState) -> dict:
    """Per-todo reconnaissance. Build a briefing for the executor."""
    todo = state["current_todo"]
    target_files = state["target_files"]

    # Read target files
    file_contents = {}
    for f in target_files:
        path = Path(f)
        if path.exists():
            content = path.read_text()
            if len(content) > 3000:
                file_contents[f] = _summarise_file(f, content)
            else:
                file_contents[f] = content
        else:
            file_contents[f] = "(does not exist yet)"

    # Trace imports one level deep
    dependency_map = {}
    for f in target_files:
        if Path(f).exists() and f.endswith((".ts", ".js", ".tsx", ".jsx")):
            result = subprocess.run(
                ["grep", "-E", "^(import|export.*from)", f],
                capture_output=True, text=True
            )
            if result.stdout.strip():
                dependency_map[f] = result.stdout.strip()

    # Find related test files
    test_files = {}
    for f in target_files:
        stem = Path(f).stem
        for pattern in [f"**/{stem}.test.ts", f"**/{stem}.spec.ts"]:
            for test_file in Path(".").glob(pattern):
                test_files[str(test_file)] = test_file.read_text()[:1000]

    # Recent git history
    git_history = ""
    for f in target_files[:5]:
        if Path(f).exists():
            log = subprocess.run(
                ["git", "log", "--oneline", "-5", "--", f],
                capture_output=True, text=True
            ).stdout
            if log:
                git_history += f"\n### {f}\n{log}"

    recon_prompt = f"""Build a briefing for this coding task.

## Todo: {todo["text"]}
## Roadmap Context
{state["roadmap"]}

## Target Files
{_format_dict(file_contents)}

## Dependencies (imports)
{_format_dict(dependency_map)}

## Related Tests
{_format_dict(test_files) if test_files else "None found."}

## Recent Git History
{git_history or "No recent changes."}

Write a concise, actionable briefing covering:
1. Current State — what exists, what needs creating
2. Dependencies — what this touches beyond target files
3. Patterns to Follow — code patterns from existing files
4. Existing Tests — what's covered, what's missing
5. Risks — things that could go wrong
"""

    response = llm.invoke(recon_prompt)

    return {"briefing": response.content, "exploration_mode": "recon"}


def _summarise_file(filepath: str, content: str) -> str:
    """For large files, extract key declarations only."""
    lines = content.split("\n")
    important = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if any(stripped.startswith(kw) for kw in [
            "export", "class ", "interface ", "type ", "function ",
            "const ", "async function", "describe(", "it(",
        ]):
            important.append(f"L{i+1}: {stripped}")
    return f"// {filepath} ({len(lines)} lines)\n" + "\n".join(important[:30])
```

### `match_rules`

```python
import yaml
from fnmatch import fnmatch


def match_rules(state: AgentState) -> dict:
    """Load path-scoped rules matching the target files."""
    target_files = state["target_files"]
    memory = state["memory"]
    active_rules = {}

    # Collect rule directories: root + per-app
    rule_dirs = [AGENT_DIR / "rules"]
    seen = set()
    for target_file in target_files:
        agent_dir = _find_nearest_agent_dir(target_file)
        rd = agent_dir / "rules"
        if rd.exists() and str(rd) not in seen:
            seen.add(str(rd))
            rule_dirs.append(rd)

    for rules_dir in rule_dirs:
        for rule_file in rules_dir.glob("**/*.md"):
            content = rule_file.read_text()
            paths = _parse_path_frontmatter(content)

            if paths is None:
                active_rules[rule_file.stem] = _strip_frontmatter(content)
            elif any(fnmatch(f, p) for p in paths for f in target_files):
                active_rules[rule_file.stem] = _strip_frontmatter(content)

    return {"memory": {**memory, "active_rules": active_rules}}


def _parse_path_frontmatter(content: str) -> list[str] | None:
    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    meta = yaml.safe_load(parts[1])
    return meta.get("paths") if meta else None


def _strip_frontmatter(content: str) -> str:
    if not content.startswith("---"):
        return content
    parts = content.split("---", 2)
    return parts[2].strip() if len(parts) >= 3 else content


def _find_nearest_agent_dir(filepath: str) -> Path:
    p = Path(filepath).parent
    while p != p.parent:
        if (p / ".agent").is_dir():
            return p / ".agent"
        p = p.parent
    return AGENT_DIR
```

### `deepen_context`

```python
def deepen_context(state: AgentState) -> dict:
    """LLM picks relevant L1/L2 memory. Also loads latest GCC commit (K=1)."""
    memory = state["memory"]
    todo = state["current_todo"]

    retrieval_prompt = f"""You are preparing context for a coding task.

Current todo: {todo["text"]}
Target files: {state["target_files"]}

Memory index (L0):
{memory["l0_index"]}

Available L1 files:
{_list_available_files(AGENT_DIR / "memory", depth=1)}

Return a JSON list of relative paths to load. Be selective.
"""

    response = llm.invoke(retrieval_prompt)
    requested = _parse_json_list(response.content)

    l1_files = {}
    l2_files = {}

    for filepath in requested:
        full_path = AGENT_DIR / "memory" / filepath
        if full_path.exists():
            l1_files[filepath] = full_path.read_text()
            # Check for L2 subdirectory
            l2_dir = full_path.with_suffix("")
            if l2_dir.is_dir():
                for l2_file in l2_dir.glob("*.md"):
                    if _is_relevant(l2_file.stem, todo["text"]):
                        key = str(l2_file.relative_to(AGENT_DIR / "memory"))
                        l2_files[key] = l2_file.read_text()

    # Load latest GCC commit for session continuity (K=1)
    session_history = ""
    commits_dir = AGENT_DIR / "gcc" / "commits"
    if commits_dir.exists():
        commits = sorted(commits_dir.glob("*.md"))
        if commits:
            session_history = commits[-1].read_text()

    # Load branch context if on a feature branch
    branch = state.get("working_branch", "main")
    branch_dir = AGENT_DIR / "gcc" / "branches" / branch
    if branch_dir.exists() and (branch_dir / "context.md").exists():
        session_history += "\n\n" + (branch_dir / "context.md").read_text()

    return {
        "memory": {
            **memory,
            "l1_files": l1_files,
            "l2_files": l2_files,
            "session_history": session_history,
        }
    }
```

### `extract_session`

```python
def extract_session(state: AgentState) -> dict:
    """Read GCC commits from this session, distill into lasting memory."""
    commits_dir = AGENT_DIR / "gcc" / "commits"
    start = state.get("session_start_commit", 0)
    all_commits = sorted(commits_dir.glob("*.md")) if commits_dir.exists() else []
    session_commits = all_commits[start:]

    if not session_commits:
        return state

    combined = "\n\n---\n\n".join(f.read_text() for f in session_commits)

    extraction_prompt = f"""Read these session commits and extract lasting knowledge.

## Session Commits
{combined}

## Current Memory Index
{state["memory"]["l0_index"]}

## Todos Completed
{chr(10).join(f'- {t}' for t in state.get('todos_completed_this_session', []))}

Extract JSON:
{{
  "memory_updates": [
    {{"file": "architecture/auth-system.md", "action": "create|append|replace_section", "section": "optional", "content": "..."}}
  ],
  "index_updates": [
    {{"old_line": "existing line or null", "new_line": "updated summary"}}
  ],
  "new_rules": [
    {{"file": "rules/auth-middleware.md", "paths": ["apps/api/src/middleware/**"], "content": "rule text"}}
  ],
  "decisions": [
    {{"summary": "one-line", "detail": "full reasoning", "alternatives_considered": "what was rejected and why"}}
  ]
}}

Rules:
- Only extract genuinely NEW knowledge not already in memory
- Decisions from exploration branches are especially valuable
- Record rejected alternatives so future agents don't re-explore
- Keep index lines under 100 characters
- Empty lists if nothing new was learned
"""

    response = llm.invoke(extraction_prompt)
    updates = _parse_json(response.content)

    _apply_memory_updates(updates.get("memory_updates", []))
    _apply_index_updates(updates.get("index_updates", []))
    _apply_new_rules(updates.get("new_rules", []))
    _apply_decisions(updates.get("decisions", []))

    # Write session summary
    from datetime import date
    session_file = AGENT_DIR / "sessions" / f"{date.today().isoformat()}.md"
    _append_or_create(session_file, _format_session_from_commits(session_commits, updates))

    return state


def should_continue(state: AgentState) -> str:
    completed = len(state.get("todos_completed_this_session", []))
    if completed >= 5:  # max_todos_per_session from config
        return "no"
    if state.get("current_todo") is not None:
        return "yes"
    return "no"
```

---

## 12. Tools

### Progress Tools

```python
from langchain_core.tools import tool
from datetime import datetime


@tool
def gcc_commit(summary: str, what_i_did: str, decisions_made: str = "",
               issues_encountered: str = "", files_touched: str = "") -> str:
    """Log structured progress. Call after completing a meaningful unit
    of work. These commits feed into memory extraction.

    Args:
        summary: One-line summary
        what_i_did: Bullet list of actions taken
        decisions_made: Any choices made and why
        issues_encountered: Problems hit and how resolved
        files_touched: Files created/modified with brief notes
    """
    commits_dir = AGENT_DIR / "gcc" / "commits"
    commits_dir.mkdir(parents=True, exist_ok=True)

    num = len(list(commits_dir.glob("*.md"))) + 1

    content = f"""# Commit {num:03d}: {summary}
**Date**: {datetime.now().isoformat()}

## What I Did
{what_i_did}
"""
    if decisions_made:
        content += f"\n## Decisions Made\n{decisions_made}\n"
    if issues_encountered:
        content += f"\n## Issues Encountered\n{issues_encountered}\n"
    if files_touched:
        content += f"\n## Files Touched\n{files_touched}\n"

    (commits_dir / f"{num:03d}.md").write_text(content)
    return f"Committed {num:03d}: {summary}"


@tool
def mark_todo_done(todo_text: str, notes: str = "") -> str:
    """Mark a todo as completed in the roadmap."""
    main_md = AGENT_DIR / "gcc" / "main.md"
    content = main_md.read_text()
    old = f"- [ ] {todo_text}"
    suffix = f" → {notes}" if notes else ""
    new = f"- [x] ~~{todo_text}~~{suffix}"
    if old in content:
        content = content.replace(old, new, 1)
        main_md.write_text(content)
        return f"Done: {todo_text}"
    return f"Not found: {todo_text}"


@tool
def add_todo(todo_text: str, after: str = "") -> str:
    """Add a discovered sub-task to the roadmap."""
    main_md = AGENT_DIR / "gcc" / "main.md"
    content = main_md.read_text()
    new_line = f"- [ ] {todo_text}"
    if after:
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if after in line:
                lines.insert(i + 1, new_line)
                break
        content = "\n".join(lines)
    else:
        content = _append_to_section(content, "## Todos", new_line)
    main_md.write_text(content)
    return f"Added: {todo_text}"


@tool
def discover_files(files: list[str]) -> str:
    """Register additional target files found during work."""
    main_md = AGENT_DIR / "gcc" / "main.md"
    content = main_md.read_text()
    added = 0
    for f in files:
        if f not in content:
            content = _append_to_section(content, "## Target Files", f"- {f}")
            added += 1
    main_md.write_text(content)
    return f"Added {added} target files."
```

### Exploration Tools

```python
@tool
def gcc_explore(question: str, approaches: list[dict]) -> str:
    """Start branching exploration with git worktrees.

    Args:
        question: The decision to explore
        approaches: [{"name": "cookies", "plan": "Use httpOnly cookies..."}, ...]
    """
    explore_id = f"explore-{datetime.now().strftime('%H%M%S')}"
    worktrees_dir = AGENT_DIR / "worktrees"
    worktrees_dir.mkdir(exist_ok=True)

    results = []
    for approach in approaches:
        name = approach["name"]
        branch_name = f"gcc/{explore_id}/{name}"
        worktree_path = worktrees_dir / explore_id / name

        subprocess.run(["git", "branch", branch_name], check=True)
        subprocess.run(
            ["git", "worktree", "add", str(worktree_path), branch_name],
            check=True
        )

        branch_dir = AGENT_DIR / "gcc" / "branches" / f"{explore_id}-{name}"
        branch_dir.mkdir(parents=True, exist_ok=True)
        (branch_dir / "commits").mkdir(exist_ok=True)
        (branch_dir / "context.md").write_text(
            f"# Branch: {name}\n"
            f"**Exploration**: {explore_id}\n"
            f"**Question**: {question}\n"
            f"**Plan**: {approach['plan']}\n"
            f"**Status**: active\n"
            f"**Worktree**: {worktree_path}\n"
        )
        results.append({"name": name, "worktree": str(worktree_path)})

    _append_to_section(
        (AGENT_DIR / "gcc" / "main.md").read_text(),
        "## Active Branches",
        f"- **{explore_id}**: {question}"
    )

    return (
        f"Exploration {explore_id} created.\n"
        + "\n".join(f"- {r['name']}: {r['worktree']}" for r in results)
    )


@tool
def gcc_try_approach(explore_id: str, approach_name: str, actions: str) -> str:
    """Log what you implemented in a worktree."""
    branch_dir = AGENT_DIR / "gcc" / "branches" / f"{explore_id}-{approach_name}"
    commits_dir = branch_dir / "commits"
    num = len(list(commits_dir.glob("*.md"))) + 1

    (commits_dir / f"{num:03d}.md").write_text(
        f"# {approach_name}: Attempt {num}\n"
        f"**Date**: {datetime.now().isoformat()}\n\n"
        f"## Actions\n{actions}\n"
    )

    worktree = AGENT_DIR / "worktrees" / explore_id / approach_name
    subprocess.run(["git", "-C", str(worktree), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(worktree), "commit", "-m",
         f"gcc: {explore_id}/{approach_name} attempt {num}"],
        capture_output=True
    )
    return f"Recorded attempt {num} for {approach_name}."


@tool
def gcc_evaluate(explore_id: str, evaluation: str,
                 winner: str, reasoning: str) -> str:
    """Compare approaches and pick a winner. Records a GCC commit
    with the full comparison for memory extraction."""
    branches_dir = AGENT_DIR / "gcc" / "branches"
    approaches = [
        d.name.replace(f"{explore_id}-", "")
        for d in branches_dir.iterdir()
        if d.name.startswith(explore_id)
    ]

    # Update branch statuses
    for approach in approaches:
        ctx = branches_dir / f"{explore_id}-{approach}" / "context.md"
        content = ctx.read_text()
        status = "winner" if approach == winner else "rejected"
        content = content.replace("**Status**: active", f"**Status**: {status}")
        content += f"\n## Evaluation\n{evaluation}\n**Reasoning**: {reasoning}\n"
        ctx.write_text(content)

    # Record as GCC commit (feeds extract_session)
    commits_dir = AGENT_DIR / "gcc" / "commits"
    num = len(list(commits_dir.glob("*.md"))) + 1

    approach_details = []
    for a in approaches:
        for cf in sorted((branches_dir / f"{explore_id}-{a}" / "commits").glob("*.md")):
            approach_details.append(f"### {a}\n{cf.read_text()}")

    (commits_dir / f"{num:03d}.md").write_text(
        f"# Commit {num:03d}: Exploration resolved — {explore_id}\n"
        f"**Date**: {datetime.now().isoformat()}\n"
        f"**Type**: exploration\n\n"
        f"## Approaches\n"
        + "\n".join(f"- **{a}**" + (" ✅" if a == winner else " ❌") for a in approaches)
        + f"\n\n## Evaluation\n{evaluation}\n\n"
        f"## Decision\nWinner: **{winner}** — {reasoning}\n\n"
        f"## Details\n" + "\n".join(approach_details)
    )

    return f"Winner: {winner}. Call gcc_adopt to apply."


@tool
def gcc_adopt(explore_id: str, winner: str) -> str:
    """Merge the winning approach and clean up worktrees."""
    winner_branch = f"gcc/{explore_id}/{winner}"

    subprocess.run(
        ["git", "merge", winner_branch, "--no-edit",
         "-m", f"gcc: adopt {explore_id}/{winner}"],
        check=True
    )

    # Clean up worktrees
    worktrees_dir = AGENT_DIR / "worktrees" / explore_id
    if worktrees_dir.exists():
        for d in worktrees_dir.iterdir():
            subprocess.run(
                ["git", "worktree", "remove", str(d), "--force"],
                capture_output=True
            )
        worktrees_dir.rmdir()

    # Clean up branches
    branches_dir = AGENT_DIR / "gcc" / "branches"
    for d in branches_dir.iterdir():
        if d.name.startswith(explore_id):
            branch_name = f"gcc/{explore_id}/{d.name.replace(f'{explore_id}-', '')}"
            subprocess.run(["git", "branch", "-D", branch_name], capture_output=True)

    _remove_active_branch(explore_id)
    return f"Adopted {winner}. Worktrees cleaned up."
```

### Memory Query Tool

```python
@tool
def memory_query(question: str) -> str:
    """Search agent memory for context. Uses git grep + LLM judgment."""
    index = (AGENT_DIR / "memory" / "_index.md").read_text()

    grep = subprocess.run(
        ["git", "grep", "-l", "-i", question.split()[0], "--", str(AGENT_DIR)],
        capture_output=True, text=True
    ).stdout

    git_log = subprocess.run(
        ["git", "log", "--oneline", "-20", "--", str(AGENT_DIR / "memory")],
        capture_output=True, text=True
    ).stdout

    prompt = f"""Question: {question}

Memory index:\n{index}
Files matching:\n{grep}
Recent changes:\n{git_log}

Which file(s) to read? Return file paths, one per line.
"""
    response = llm.invoke(prompt)
    paths = [p.strip() for p in response.content.strip().split("\n") if p.strip()]

    parts = []
    for p in paths:
        full = Path(p)
        if full.exists():
            parts.append(f"### {p}\n{full.read_text()}")

    return "\n\n".join(parts) if parts else "No relevant memory found."
```

---

## 13. Graph Assembly

```python
from langgraph.graph import StateGraph, START, END


def build_agent_graph():
    graph = StateGraph(AgentState)

    graph.add_node("load_context", load_context)
    graph.add_node("explore_bootstrap", explore_bootstrap)
    graph.add_node("read_roadmap", read_roadmap)
    graph.add_node("check_first_todo", lambda s: s)
    graph.add_node("explore_validate", explore_validate)
    graph.add_node("explore_recon", explore_recon)
    graph.add_node("match_rules", match_rules)
    graph.add_node("deepen_context", deepen_context)
    graph.add_node("execute_todo", execute_todo)
    graph.add_node("extract_session", extract_session)
    graph.add_node("roadmap_done", roadmap_done)

    # Startup
    graph.add_edge(START, "load_context")
    graph.add_conditional_edges("load_context", needs_bootstrap, {
        "yes": "explore_bootstrap", "no": "read_roadmap",
    })
    graph.add_edge("explore_bootstrap", "read_roadmap")

    # Roadmap loop
    graph.add_conditional_edges("read_roadmap", has_todo, {
        "yes": "check_first_todo", "no": "roadmap_done",
    })
    graph.add_conditional_edges("check_first_todo", is_first_todo, {
        "yes": "explore_validate", "no": "explore_recon",
    })
    graph.add_edge("explore_validate", "explore_recon")

    # Context → execution
    graph.add_edge("explore_recon", "match_rules")
    graph.add_edge("match_rules", "deepen_context")
    graph.add_edge("deepen_context", "execute_todo")

    # Post-execution
    graph.add_edge("execute_todo", "extract_session")
    graph.add_conditional_edges("extract_session", should_continue, {
        "yes": "read_roadmap", "no": END,
    })
    graph.add_edge("roadmap_done", "extract_session")

    return graph.compile()
```

---

## 14. System Prompt Assembly

```python
def build_system_prompt(state: AgentState) -> str:
    memory = state["memory"]
    todo = state.get("current_todo")
    sections = []

    if todo:
        sections.append(
            f"# Current Objective\n"
            f"Working on: **{todo['text']}**\n\n"
            f"Full roadmap:\n{state['roadmap']}"
        )

    if state.get("briefing"):
        sections.append(f"# Codebase Briefing\n{state['briefing']}")

    sections.append(f"# Project Context\n{memory['l0_index']}")

    if memory["active_rules"]:
        rules = "\n\n".join(f"## {n}\n{c}" for n, c in memory["active_rules"].items())
        sections.append(f"# Rules (MUST follow)\n{rules}")

    for n, c in memory.get("l1_files", {}).items():
        sections.append(f"# Memory: {n}\n{c}")
    for n, c in memory.get("l2_files", {}).items():
        sections.append(f"# Detail: {n}\n{c}")

    if memory.get("session_history"):
        sections.append(f"# Previous Progress\n{memory['session_history']}")

    return "\n\n---\n\n".join(sections)
```

---

## 15. Lifecycle

```
GitLab Issue #142
        │
        ▼ (planner / human)
Seed .agent/gcc/main.md
        │
        ▼ (agent graph)
Bootstrap? ──yes──► Scan repo, build memory + rules
        │
        ▼
Validate roadmap ──► Correct files, discover deps, add constraints
        │
        ▼
┌─── Per-todo loop ────────────────────────────────────────────┐
│                                                               │
│  1. Recon: read files, trace imports, build briefing          │
│  2. Match rules: load path-scoped rules for target files      │
│  3. Deepen context: load relevant L1/L2 memory + K=1 commit  │
│  4. Execute: write code, gcc_commit progress                  │
│     └─ If uncertain: gcc_explore → try in worktrees           │
│        → gcc_evaluate → gcc_adopt winner                      │
│  5. Extract: read commits → update memory/rules/decisions     │
│                                                               │
│  Loop until all todos done or budget exhausted                │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
Archive roadmap, clear main.md
Git commit + MR (code + memory + rules + reasoning)
```

---

## 16. What Each GCC Piece Does

| Piece | Written by | Read by | Purpose |
|-------|-----------|---------|---------|
| `main.md` | Planner seed + agent tools | `read_roadmap` every loop | Task driver + progress tracker |
| `commits/*.md` | `gcc_commit` during execution | `extract_session` + `deepen_context` (K=1) | Session log → memory extraction; session recovery |
| `branches/*/context.md` | `gcc_explore` | `gcc_evaluate` + `extract_session` | Exploration purpose + outcome |
| `branches/*/commits/*.md` | `gcc_try_approach` | `gcc_evaluate` + `extract_session` | What was tried per approach |

Nothing is written without being read.

---

## 17. Config

```yaml
# .agent/config.yaml

loading:
  l0_max_tokens: 500
  l1_max_tokens: 2000
  l2_max_tokens: 4000
  max_total_context: 12000

rules:
  global_rules_dir: ".agent/rules"
  per_app_rules: true

gcc:
  max_main_md_lines: 60
  k: 1
  archive_on_complete: true
  worktrees_dir: ".agent/worktrees"
  cleanup_worktrees_on_adopt: true

explorer:
  bootstrap_on_empty: true
  validate_new_roadmaps: true
  recon_before_todo: true
  max_file_read_size: 5000
  trace_import_depth: 1
  include_git_history: true

sessions:
  auto_extract: true
  retention_days: 30
  extract_rules: true
  extract_decisions: true

retrieval:
  strategy: "llm"
  git_log_depth: 20

execution:
  max_todos_per_session: 5
  max_tool_calls_per_todo: 50
```

```gitignore
# Add to .gitignore
.agent/worktrees/
```

---

## 18. Design Decisions

### Why the roadmap IS the task
One source of truth. Progress tracked automatically. Sub-task discovery
via `add_todo`. Session continuity by re-reading `main.md`. Clean
pipeline from GitLab Issue → roadmap → execution → MR.

### Why GCC commits are the session log
The executor needs to log progress anyway. Making commits the input to
extraction eliminates a phantom `session_log` and gives every commit a
reader. Structured format (What I Did, Decisions, Issues, Files) is the
contract between executor and extractor.

### Why real worktrees for exploration
Reasoning about trade-offs isn't enough for implementation decisions.
The agent writes real code, runs real tests, compares real results.
The losing approach is recorded so future agents don't re-explore it.

### Why an explorer agent
The gap between "plan from issue description" and "code that actually
exists" is where agents fail. Bootstrap builds understanding. Validate
catches wrong assumptions. Recon gives per-todo briefings. The executor
never writes code blind.

### Why LLM-driven retrieval instead of vectors
For hundreds of memory files (not millions), the LLM reading a
structured index is more inspectable, debuggable, and infrastructure-free
than vector search. The explorer provides the grounding that vectors
would otherwise give.

### Why three layers
Memory is context (loaded by relevance). Rules are instructions (loaded
by path). GCC is intent (loaded always/by recency). Each uses the
optimal loading strategy without interference.
