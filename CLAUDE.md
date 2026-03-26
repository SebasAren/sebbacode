# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Install (editable)
uv pip install -e .

# Run the agent
sebba-code run --verbose          # or: mise run run
sebba-code init                   # create .agent/ structure
sebba-code seed "Issue title"     # seed roadmap from description

# Tests
uv run pytest tests/ -v           # or: mise run test
pytest tests/test_nodes/test_roadmap.py   # single file

# Lint/format (not configured in project, but available)
ruff check src/sebba_code/
mypy src/sebba_code/
```

## Architecture

sebba-code is a **LangGraph coding agent** that executes a roadmap of tasks from `.agent/roadmap.md`, using LLM-guided tool calls. It persists knowledge across sessions via tiered memory.

### Graph Flow (11 nodes)

Defined in `src/sebba_code/graph.py`:

```
START → load_context → [needs_bootstrap?]
  yes → explore_bootstrap → read_roadmap
  no  → read_roadmap → [has_todo?]
    no  → roadmap_done → extract_session → END
    yes → [is_first_todo?]
      yes → explore_validate → explore_recon
      no  → explore_recon
    → match_rules → deepen_context → execute_todo (subgraph)
    → finalize_todo → extract_session → [should_continue?]
      yes → read_roadmap (loop)
      no  → END
```

- **execute_todo** is a subgraph with an inner LLM+tools loop (max 50 tool calls per todo)
- **finalize_todo** marks the todo done in the roadmap and creates a summary in LangGraph state
- **extract_session** distills todo summaries from state into lasting memory/rules
- **roadmap_done** archives the completed roadmap to `.agent/roadmaps/archive/`
- Session processes up to 5 todos before stopping

### Tiered Memory System

All memory lives under `.agent/memory/`:
- **L0** (`_index.md`): Always loaded, ~500 tokens. One-liner summaries.
- **L1** (`architecture.md`, `conventions.md`): Loaded on demand, ~2000 tokens each.
- **L2** (subdirectories like `architecture/`, `patterns/`): Deep-dive files, ~4000 tokens. Selected by LLM in `deepen_context` node.

### Key Concepts

- **Roadmap**: Markdown file at `.agent/roadmap.md` with `- [ ] todo` items driving execution. Completed roadmaps are archived to `.agent/roadmaps/archive/`.
- **Todo summaries**: Per-todo progress summaries stored in LangGraph state (not files), created by `finalize_todo` via cheap LLM summarization of the message history.
- **Path-scoped rules**: Files in `.agent/rules/` with YAML frontmatter `paths:` globs — matched against target files in `match_rules` node
- **Exploration via worktrees**: `explore` creates git worktrees for parallel experimentation; `adopt` merges the winner. Branch context stored in `.agent/branches/`.

### Source Layout

- `src/sebba_code/nodes/` — Graph node functions (context loading, exploration, execution, extraction)
- `src/sebba_code/tools/` — 11 LLM-callable tools (file I/O, shell, progress tracking, exploration, memory query)
- `src/sebba_code/helpers/` — Utilities for git, markdown manipulation, memory ops, rule parsing

## Configuration

Config loaded from `.agent/config.yaml` with dataclass defaults in `src/sebba_code/config.py`.

LLM settings fall back to `SEBBA_*` environment variables:
- `SEBBA_MODEL` / `SEBBA_MODEL_PROVIDER` / `SEBBA_BASE_URL` / `SEBBA_API_KEY` — main model
- `SEBBA_CHEAP_MODEL` / `SEBBA_CHEAP_MODEL_PROVIDER` / `SEBBA_CHEAP_BASE_URL` / `SEBBA_CHEAP_API_KEY` — cheap model (used for extraction, context selection)

Defaults: `claude-sonnet-4-6` (main), `claude-haiku-4-5-20251001` (cheap). The `mise.toml` in this repo overrides these to use a custom OpenAI-compatible endpoint.
