# sebba-code

A LangGraph coding agent with git-native memory. The agent's knowledge, rules, and progress all live as Markdown files in your `.agent/` directory — version-controlled, diffable, and always in sync with your codebase.

## Architecture

sebba-code executes todos from a roadmap using a LangGraph state machine:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Agent Graph                             │
│  load_context → read_roadmap → execute_todo → extract_session   │
│         ↓              ↓              ↓              ↓         │
│   explore_bootstrap  has_todo?    mark_todo_done  roadmap_done  │
│                            → match_rules → deepen_context       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    .agent/
                    ├── memory/          # L0/L1/L2 knowledge
                    ├── rules/           # Path-scoped imperatives
                    ├── roadmap.md       # Task backlog
                    ├── branches/        # Exploration records
                    ├── sessions/        # Session logs
                    ├── worktrees/       # Git worktrees for exploration
                    └── config.yaml      # Agent configuration
```

### Graph Flow

The main graph orchestrates three phases:

1. **Load & Bootstrap** — Load L0 memory index, detect git state, bootstrap if codebase is new
2. **Explore & Prepare** — Validate/recon the target files, load matching rules, deepen context
3. **Execute & Extract** — Run the inner todo loop, sync progress, distill learnings into memory

The `execute_todo` node is itself a subgraph that loops LLM calls → tool execution until done.

### Tiered Memory

Memory is loaded in three tiers to manage context:

| Layer | Files | When Loaded | Token Budget |
|-------|-------|-------------|--------------|
| L0 | `_index.md` | Always | ~500 tokens |
| L1 | `architecture.md`, `conventions.md` | On relevance | ~2000 tokens each |
| L2 | `architecture/auth-system.md` etc. | On demand | ~4000 tokens |

### Execute Subgraph

The `execute_todo` subgraph provides the agent's tool-calling loop:

```
llm_call → [tool_calls?] → tools → llm_call
                        ↓ (no calls)
                       END
```

Each iteration assembles a system prompt from roadmap, context, rules, and memory, then invokes the LLM with all bound tools. The loop continues until the LLM returns without tool calls.

### Planning Loop

For roadmap creation, a separate planning graph implements an iterative draft-critique-refine cycle:

```
draft_roadmap → critique_roadmap → refine_roadmap → write_roadmap
                     ↓
              planning_complete?
```

- **draft_roadmap**: Creates initial roadmap from user request
- **critique_roadmap**: Evaluates with cheap model, identifies issues
- **refine_roadmap**: Addresses critique, can iterate up to max_iterations
- **write_roadmap**: Commits final roadmap to `.agent/roadmap.md`

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
| `run` | `--dry-run` | Print next roadmap todo and exit without executing |
| `run` | `--debug-prompts` | Log prompts and message summaries at each LLM call |
| `run` | `--max-todos N` | Override the session limit of 5 todos |
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

# Preview what the agent will do
sebba-code run --dry-run

# Run with verbose output
sebba-code run --verbose

# Debug LLM prompts
sebba-code run --debug-prompts

# Limit to 2 todos per session
sebba-code run --max-todos 2

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

loading:
  l0_max_tokens: 500        # Always loaded index
  l1_max_tokens: 2000       # On-demand top-level docs
  l2_max_tokens: 4000       # Deep-dive subdirectory docs

explorer:
  bootstrap_on_empty: true
  validate_new_roadmaps: true
  recon_before_todo: true

sessions:
  auto_extract: true
  retention_days: 30
  extract_rules: true

execution:
  max_todos_per_session: 5 # Auto-extract after this many
  max_tool_calls_per_todo: 50

planning:
  max_iterations: 3        # Draft-critique-refine cycles
  # model: ""               # Override model for planning only
  auto_approve: false
```

Environment variables also work:

```bash
export SEBBA_API_KEY="sk-ant-..."
export SEBBA_MODEL="claude-sonnet-4-6"
sebba-code run
```

## Roadmap Format

The roadmap (`.agent/roadmap.md`) is the agent's task backlog:

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
# Session Summary: Created auth middleware

**Date**: 2026-03-25T14:30:00
**Todo**: Create auth middleware with token validation

## What I Did
- Created apps/api/src/middleware/auth.ts
- Added verifyToken import from shared-lib
- Registered middleware in app.ts

## Decisions Made
- Cookie extraction over Authorization header (httpOnly = more secure)

## Issues Encountered
- shared-lib was missing TokenPayload export → added it

## Files Touched
- apps/api/src/middleware/auth.ts (created)
- apps/api/src/app.ts (modified)
```

These summaries feed the `extract_session` node after each todo, distilling new knowledge into memory.

## Agent Tools

The execution subgraph provides these tools:

| Tool | Purpose |
|------|---------|
| `mark_todo_done` | Mark item complete in roadmap |
| `add_todo` | Add discovered sub-task |
| `discover_files` | Register additional target files |
| `memory_query` | Search agent memory for context |
| `explore` | Start branch exploration with git worktrees |
| `try_approach` | Log what you implemented in a worktree |
| `evaluate` | Compare approaches and pick a winner |
| `adopt` | Merge winning approach and clean up worktrees |
| `read_file` | Read file contents |
| `run_command` | Execute shell command |
| `write_file` | Write content to file |

## Graph Nodes

```
load_context        → Load L0/L1/L2 memory, check if bootstrap needed
explore_bootstrap   → On empty codebase, explore and document structure
read_roadmap        → Parse roadmap.md, extract current todo and target files
explore_validate    → Validate roadmap (first todo only)
explore_recon       → Ground target files in actual codebase
match_rules         → Load rules matching target file paths
deepen_context      → LLM decides which L2 files to read
execute_todo        → Inner loop: LLM call → tool execution → repeat
extract_session     → Distill session summaries into memory/decisions/rules
roadmap_done        → Handle completion (archive, next roadmap)
```

### Planning Graph Nodes

```
draft_roadmap       → Generate initial roadmap from user request
critique_roadmap    → Evaluate with cheap model, identify issues
refine_roadmap       → Address critique, iterate if needed
write_roadmap       → Commit final roadmap to .agent/roadmap.md
```

### State Flow

```python
AgentState {
    messages: Annotated[list[BaseMessage], add_messages]

    # Roadmap-driven
    roadmap: str
    current_todo: TodoItem | None
    target_files: list[str]

    # Explorer output
    briefing: str
    exploration_mode: str

    # Memory
    memory: AgentMemoryContext {
        l0_index: str
        l1_files: dict[str, str]
        l2_files: dict[str, str]
        active_rules: dict[str, str]
        session_history: str
    }

    # Git
    working_branch: str | None

    # Session tracking
    todos_completed_this_session: list[str]
    todo_summaries: list[TodoSummary]

    # Configurable limits
    max_todos: int | None
}
```

## Development

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# With coverage
pytest --cov=sebba_code
```

## Project Structure

```
sebba_code/
├── __init__.py              # Package entry, version
├── __main__.py              # CLI entry point
├── cli.py                   # Click CLI commands
├── config.py                # Configuration dataclasses
├── constants.py             # Agent directory paths
├── graph.py                 # Main LangGraph assembly
├── llm.py                   # LLM provider configuration
├── prompts.py               # System prompt building
├── seed.py                  # Roadmap initialization
├── state.py                 # TypedDict state schemas
├── plan_graph.py            # Planning loop graph
├── planning_prompts.py      # Planning prompt templates
├── nodes/
│   ├── __init__.py
│   ├── context.py           # Memory loading logic
│   ├── done.py              # Roadmap completion handling
│   ├── execute.py            # Todo execution subgraph
│   ├── extract.py           # Session distillation
│   ├── explore.py            # Bootstrap and validation
│   ├── load_context.py      # Initial context loading
│   ├── planning.py          # Planning loop nodes
│   ├── roadmap.py           # Roadmap parsing
│   └── rules.py             # Rules matching
├── tools/
│   ├── __init__.py
│   ├── code.py              # File I/O tools
│   ├── exploration.py       # Git worktree tools
│   ├── memory.py             # Memory query tool
│   └── progress.py           # Todo management tools
├── helpers/
│   ├── __init__.py
│   ├── files.py              # File utilities
│   ├── git.py                # Git operations
│   ├── markdown.py           # Markdown parsing/writing
│   ├── memory_ops.py         # Memory operations
│   ├── parsing.py            # Parsing utilities
│   └── rules_ops.py          # Rules operations
└── tests/
    ├── conftest.py
    ├── test_helpers/
    └── test_nodes/
```

## License

MIT
