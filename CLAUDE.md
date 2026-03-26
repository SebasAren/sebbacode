# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Install (editable)
uv pip install -e .

# Run the agent
sebba-code run "Build feature X" --verbose
sebba-code run "Fix bug Y" --auto-approve
sebba-code init                   # create .agent/ structure
sebba-code plan "Description"     # preview task DAG without executing

# Tests
uv run pytest tests/ -v           # or: mise run test
pytest tests/test_nodes/test_dispatch.py  # single file

# Lint/format (not configured in project, but available)
ruff check src/sebba_code/
mypy src/sebba_code/
```

## Architecture

sebba-code is a **LangGraph coding agent** with unified planning + parallel DAG execution. Tasks live entirely in LangGraph state (no roadmap files). It persists knowledge across sessions via tiered memory.

### Graph Flow (12 nodes)

Defined in `src/sebba_code/graph.py`:

```
START → load_context → [needs_bootstrap?]
  yes → explore_bootstrap → plan_draft
  no  → plan_draft → plan_critique → [complete?]
    no  → plan_refine → plan_critique (loop)
    yes → build_dag → human_approval → [approve?]
      reject → plan_draft (with feedback)
      approve → dispatch_tasks → [Send() fan-out]
        → task_worker (×N parallel) → collect_results
        → [more ready?] → dispatch_tasks (loop)
        → [all done] → extract_session → END
```

- **plan_draft** generates a JSON task plan with dependency edges
- **human_approval** uses `interrupt()` for user review; rejected plans loop back with feedback
- **dispatch_tasks** computes ready tasks from the DAG and fans out via `Send()`
- **task_worker** is a subgraph: recon → rules → context → LLM+tools loop → summarize → extract
- **collect_results** merges results, applies DAG mutations (new tasks, blocks), routes next wave
- **extract_session** applies collected memory updates and writes session summary

### Tiered Memory System

All memory lives under `.agent/memory/`:
- **L0** (`_index.md`): Always loaded, ~500 tokens. One-liner summaries.
- **L1** (`architecture.md`, `conventions.md`): Loaded on demand, ~2000 tokens each.
- **L2** (subdirectories like `architecture/`, `patterns/`): Deep-dive files, ~4000 tokens. Selected by LLM in `deepen_context` node.

### Key Concepts

- **Task DAG**: Tasks with `depends_on` edges stored in LangGraph state. Independent tasks run in parallel.
- **Human-in-the-loop**: Plan approval via `interrupt()` + `Command` routing. Rejection feeds back to planning.
- **Per-task memory extraction**: Each worker collects memory updates; applied sequentially by `extract_session`.
- **Dynamic DAG mutations**: Workers can signal blocks or add subtasks via tools, applied between dispatch waves.
- **Path-scoped rules**: Files in `.agent/rules/` with YAML frontmatter `paths:` globs — matched against target files.

### Source Layout

- `src/sebba_code/nodes/` — Graph node functions (planning, approval, dispatch, worker, extraction)
- `src/sebba_code/tools/` — LLM-callable tools (file I/O, shell, task management, memory query)
- `src/sebba_code/helpers/` — Utilities for git, markdown manipulation, memory ops, rule parsing

## Configuration

Config loaded from `.agent/config.yaml` with dataclass defaults in `src/sebba_code/config.py`.

LLM settings fall back to `SEBBA_*` environment variables:
- `SEBBA_MODEL` / `SEBBA_MODEL_PROVIDER` / `SEBBA_BASE_URL` / `SEBBA_API_KEY` — main model
- `SEBBA_CHEAP_MODEL` / `SEBBA_CHEAP_MODEL_PROVIDER` / `SEBBA_CHEAP_BASE_URL` / `SEBBA_CHEAP_API_KEY` — cheap model (used for extraction, context selection)

Defaults: `claude-sonnet-4-6` (main), `claude-haiku-4-5-20251001` (cheap). The `mise.toml` in this repo overrides these to use a custom OpenAI-compatible endpoint.
