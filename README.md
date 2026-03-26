# sebba-code

A LangGraph coding agent with git-native memory. The agent's knowledge, rules, and progress all live as Markdown files in your `.agent/` directory — version-controlled, diffable, and always in sync with your codebase.

## Architecture

sebba-code executes tasks using a LangGraph state machine with DAG-based parallel execution:

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Agent Graph                                   │
│                                                                       │
│  load_context → [bootstrap?] → plan_draft → plan_critique           │
│         ↓              ↓            ↓                               │
│  explore_bootstrap    START      [complete?] → build_dag            │
│                                             ↓                        │
│                                     human_approval                   │
│                                             ↓                        │
│                              dispatch_tasks → [task_worker(s)]       │
│                                    ↓              ↓                 │
│                              [more tasks?]    collect_results       │
│                                    ↓              ↓                 │
│                              dispatch_tasks → extract_session → END │
└──────────────────────────────────────────────────────────────────────┘
                              ↓
                    .agent/
                    ├── memory/          # L0/L1/L2 knowledge
                    ├── rules/           # Path-scoped imperatives
                    ├── roadmap.md       # Task backlog (DAG source)
                    ├── branches/        # Exploration records
                    ├── sessions/        # Session logs
                    ├── worktrees/       # Git worktrees for exploration
                    └── config.yaml      # Agent configuration
```

### Graph Flow

The main graph orchestrates four phases:

1. **Load & Bootstrap** — Load L0 memory index, detect git state, bootstrap if codebase is new
2. **Plan** — Draft roadmap with iterative critique-refine, build task DAG
3. **Execute** — Dispatch tasks to parallel workers with human approval gating
4. **Extract** — Distill learnings into memory, archive completed roadmap

### Tiered Memory

Memory is loaded in three tiers to manage context:

| Layer | Files | When Loaded | Token Budget |
|-------|-------|-------------|--------------|
| L0 | `_index.md` | Always | ~500 tokens |
| L1 | `architecture.md`, `conventions.md` | On relevance | ~2000 tokens each |
| L2 | `architecture/auth-system.md` etc. | On demand | ~4000 tokens |

### Task Worker Subgraph

Each task executes via a dedicated worker subgraph:

```
worker_recon → worker_match_rules → worker_deepen_context → llm_call
                                                              ↓
                                                    [tool_calls?]
                                                     ↓         ↓
                                                   tools    END
```

- **worker_recon**: Builds task briefing from target files, imports, tests, git history
- **worker_match_rules**: Loads path-scoped rules for target files
- **worker_deepen_context**: LLM selects relevant L1/L2 memory
- **llm_call**: Invoke LLM with tools, loop until done or max_calls reached

### Planning Loop

For roadmap creation, an iterative draft-critique-refine cycle:

```
draft_roadmap → critique_roadmap → refine_roadmap → build_dag
                     ↓
              planning_complete?
```

- **draft_roadmap**: Creates initial roadmap from user request
- **critique_roadmap**: Evaluates with cheap model, identifies issues
- **refine_roadmap**: Addresses critique, can iterate up to max_iterations
- **build_dag**: Converts roadmap todos into executable task DAG

## Installation

```bash
# Install with uv (recommended)
uv pip install -e .

# Or with pip
pip install -e .
```

Requires Python 3.11+.

## CLI Reference

| Command | Flag | Description |
|---------|------|-------------|
| `run` | `--verbose`, `-v` | Enable DEBUG-level logging |
| `run` | `--debug-prompts` | Log prompts and message summaries at each LLM call |
| `run` | `--auto-approve` | Skip human approval step and auto-approve plan |
| `init` | — | Create the `.agent/` directory structure |
| `seed` | `--description`, `-d` | Issue description for roadmap generation |
| `seed` | `--labels`, `-l` | Labels to include in roadmap |
| `seed` | `--refine` | Use the planning loop for iterative refinement |
| `plan` | `--iterations`, `-i` | Override max planning iterations (default: 3) |
| `status` | — | Print summary of roadmap progress and memory files |

### Global Options

| Option | Default | Description |
|--------|---------|-------------|
| `--agent-dir` | `.agent` | Path to the agent directory |

## Quick Start

```bash
# 1. Initialize the .agent/ directory structure
sebba-code init

# 2. Seed a roadmap from an issue
sebba-code seed "Implement user authentication" -d "Add JWT-based auth" -l "auth,backend"

# 3. Run the agent
sebba-code run

# Run with verbose output
sebba-code run --verbose

# Debug LLM prompts
sebba-code run --debug-prompts

# Auto-approve plan without prompting
sebba-code run --auto-approve

# Check agent status
sebba-code status

# Use planning loop for refined roadmap
sebba-code seed "Build auth system" --refine

# Or use plan mode standalone
sebba-code plan "Build user authentication with JWT tokens"
sebba-code plan "Add caching layer" -i 5  # Custom iterations
```

## Configuration

Edit `.agent/config.yaml`:

```yaml
llm:
  model: "claude-sonnet-4-6"
  # model_provider: "anthropic"    # auto-detected from model name
  # base_url: ""                   # custom API endpoint
  # api_key: ""                    # override env var
  cheap_model: "claude-haiku-4-5-20251001"  # For critique/evaluate steps
  # cheap_model_provider: ""       # auto-detected from cheap_model name
  # cheap_base_url: ""             # custom cheap model endpoint
  # cheap_api_key: ""              # override cheap model API key

loading:
  l0_max_tokens: 500        # Always loaded index
  l1_max_tokens: 2000       # On-demand top-level docs
  l2_max_tokens: 4000       # Deep-dive subdirectory docs
  max_total_context: 12000  # Total context budget

explorer:
  bootstrap_on_empty: true
  max_file_read_size: 5000  # Characters before summarization
  trace_import_depth: 1     # Import tracing depth
  include_git_history: true # Include git history in briefings

rules:
  global_rules_dir: ".agent/rules"
  per_app_rules: true       # Enable app-scoped rules

sessions:
  auto_extract: true
  retention_days: 30
  extract_rules: true

retrieval:
  strategy: "llm"           # Memory retrieval strategy
  git_log_depth: 20         # Git history lines for context

execution:
  max_parallel_workers: 3   # Parallel task workers
  max_tool_calls_per_task: 50
  llm_timeout: 120          # Seconds per LLM call

planning:
  max_iterations: 3         # Draft-critique-refine cycles
  # model: ""               # Override model for planning only
  auto_approve: false
```

### Environment Variables

All configuration can be set via environment variables (with config.yaml taking precedence):

| Variable | Description | Default |
|----------|-------------|---------|
| `SEBBA_API_KEY` | LLM API key | — |
| `SEBBA_MODEL` | LLM model name | `claude-sonnet-4-6` |
| `SEBBA_MODEL_PROVIDER` | Model provider (auto-detected) | — |
| `SEBBA_BASE_URL` | Custom API endpoint | — |
| `SEBBA_CHEAP_MODEL` | Cheap model for critique/evaluate | `claude-haiku-4-5-20251001` |
| `SEBBA_CHEAP_MODEL_PROVIDER` | Cheap model provider | — |
| `SEBBA_CHEAP_BASE_URL` | Cheap model API endpoint | — |
| `SEBBA_CHEAP_API_KEY` | Cheap model API key | — |

```bash
export SEBBA_API_KEY="your-api-key-here"
export SEBBA_MODEL="claude-sonnet-4-6"
export SEBBA_CHEAP_MODEL="claude-haiku-4-5-20251001"
sebba-code run
```

## Roadmap Format

The roadmap (`.agent/roadmap.md`) is the agent's task backlog and DAG source:

```markdown
# Implement User Authentication

## Goal
Add JWT-based authentication to the API app.

## Context
Part of GitLab Issue #142. The API currently has no auth.

## Todos
- [ ] Create auth middleware
- [ ] Add login/register endpoints
- [ ] Write auth tests

## Target Files
- apps/api/src/middleware/auth.ts
- apps/api/src/routes/auth/

## Active Branches
None.

## Decisions Made
None yet.

## Constraints
- Must use shared-lib for token signing
- Error responses follow RFC 7807
```

## Memory Architecture

### Tiered Loading

| Layer | Files | When Loaded | Token Budget |
|-------|-------|-------------|--------------|
| L0 | `_index.md` files | Always | ~500 tokens |
| L1 | `architecture.md`, `conventions.md` | On relevance | ~2000 tokens each |
| L2 | `architecture/auth-system.md` etc. | On demand | ~4000 tokens |

### Memory Index Example

```markdown
<!-- .agent/memory/_index.md -->
# Agent Memory Index

- **architecture**: Monorepo with api and frontend apps, shared packages
- **conventions**: TypeScript strict mode, vitest for testing, Zod validation
- **decisions**: JWT over sessions (2026-03-20), adopted Zod (2026-03-25)
- **auth**: JWT + refresh tokens in httpOnly cookies
```

## Rules System

Rules are Markdown files with optional path scopes:

```yaml
<!-- .agent/rules/testing.md -->
---
paths:
  - "**/*.test.ts"
  - "**/*.spec.ts"
---
# Testing Rules

- Use vitest, not jest
- Every test file must have a describe block matching the module name
- Use factory functions for test data, never inline objects
```

Rules without `paths:` are global — always loaded.

## Session Summaries

After completing todos, the agent extracts session summaries that distill learnings into memory:

```markdown
# Session Summary:

... (truncated, 14389 total chars)
8cb9964 fix: enforce hard timeout on worker summarize/extract LLM calls
76edb05 fix: prevent workers from creating markdown deliverables on disk
4e61496 fix: add worker resilience — LLM timeouts, loop limits, and DAG-aware failure recovery
8f9b844 fix: add WorkerOutput schema to prevent parallel memory merge conflict
355ed47 fix: handle directory paths in worker_recon target_files
ddbbef7 fix: add task_results to WorkerState so worker results merge into parent state
ad11d07 fix: rename WorkerState.briefing to worker_briefing to avoid parallel merge conflict
547f7cc feat: temp changes
2c1b933 refactor: replace roadmap with state-driven DAG and parallel execution
ce8c4e3 chore: clean up .agent/ directory after GCC removal
```

## What I Did

This is a high-level summary of the implementation.

## Decisions Made

Key architectural decisions and their rationale.

## Issues Encountered

Problems encountered during execution and how they were resolved.

## Files Touched

List of files created or modified during the session.

## Agent Tools

### Exploration Tools

Tools for exploring the codebase and git history.

## Graph Nodes

### Main Graph Nodes

The main graph consists of 12 nodes that orchestrate the agent workflow.

### Worker Subgraph Nodes

Each task worker runs a subgraph for focused execution.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## Project Structure

```
sebba_code/
├── __init__.py          # Package entry
├── __main__.py          # CLI entry point
├── cli.py               # CLI commands
├── config.py            # Configuration loading
├── constants.py         # Constants
├── graph.py            # LangGraph assembly
├── llm.py              # LLM configuration
├── prompts.py           # System prompts
├── seed.py             # Roadmap seeding
├── state.py             # State definitions
├── nodes/              # Graph nodes
│   ├── approval.py
│   ├── context.py
│   ├── dispatch.py
│   ├── execute.py
│   ├── explore.py
│   ├── extract.py
│   ├── load_context.py
│   ├── planning.py
│   ├── rules.py
│   └── worker.py
├── tools/              # Agent tools
│   └── ...
└── helpers/            # Utilities
    └── ...
```

## License
