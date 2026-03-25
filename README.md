# sebba-code

A LangGraph coding agent with git-native memory. The agent's knowledge, rules, and progress all live as Markdown files in your `.agent/` directory — version-controlled, diffable, and always in sync with your codebase.

## Overview

sebba-code is an AI coding agent that:

- **Drives execution from a roadmap** stored in `.agent/gcc/main.md`
- **Persists memory as Markdown** in `.agent/memory/` with tiered loading (L0/L1/L2)
- **Logs progress as GCC commits** in `.agent/gcc/commits/` that feed memory extraction
- **Explores branches using git worktrees** for parallel experimentation
- **Uses path-scoped rules** to enforce conventions per file type or directory

```
┌─────────────────────────────────────────────────────────────────┐
│                         Agent Graph                             │
│  load_context → read_roadmap → execute_todo → extract_session   │
│         ↓              ↓              ↓              ↓         │
│   explore_bootstrap  has_todo?    gcc_commit()     should_      │
│                            → match_rules → deepen_context       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    .agent/
                    ├── memory/          # L0/L1/L2 knowledge
                    ├── rules/           # Path-scoped imperatives
                    ├── gcc/
                    │   ├── main.md      # Roadmap (task backlog)
                    │   ├── commits/     # Session log
                    │   └── branches/    # Exploration records
                    └── config.yaml      # Agent configuration
```

## Installation

```bash
# Install from source
pip install -e .

# Or with uv
uv pip install -e .
```

## Quick Start

```bash
# 1. Initialize the .agent/ directory structure
sebba-code init

# 2. Seed a roadmap (or create .agent/gcc/main.md manually)
sebba-code seed "Implement user authentication"

# 3. Run the agent
sebba-code run

# With verbose logging
sebba-code run --verbose
```

## Configuration

Edit `.agent/config.yaml`:

```yaml
llm:
  model: "claude-sonnet-4-6"
  # model_provider: "anthropic"    # auto-detected from model name
  # base_url: ""                   # custom API endpoint
  # api_key: ""                    # override env var

loading:
  l0_max_tokens: 500        # Always loaded index
  l1_max_tokens: 2000       # On-demand top-level docs
  l2_max_tokens: 4000       # Deep-dive subdirectory docs

gcc:
  max_main_md_lines: 60     # Keep roadmap focused
  k: 1                      # Recent commits to show
  archive_on_complete: true

execution:
  max_todos_per_session: 5 # Auto-extract after this many
  max_tool_calls_per_todo: 50
```

Environment variables also work:

```bash
export SEBBA_API_KEY="sk-ant-..."
export SEBBA_MODEL="claude-sonnet-4-6"
sebba-code run
```

## Roadmap Format

The roadmap (`.agent/gcc/main.md`) is the agent's task backlog:

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

## GCC Commit Format

During execution, the agent logs progress with `gcc_commit()`:

```markdown
# Commit 003: Created auth middleware

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

These commits feed the `extract_session` node after each todo, distilling new knowledge into memory.

## Agent Tools

The execution subgraph provides these tools:

| Tool | Purpose |
|------|---------|
| `gcc_commit` | Log structured progress |
| `mark_todo_done` | Mark item complete in roadmap |
| `add_todo` | Add discovered sub-task |
| `discover_files` | Register additional target files |
| `memory_query` | Search agent memory for context |
| `gcc_explore` | Start branch exploration |
| `gcc_try_approach` | Log worktree implementation |
| `gcc_evaluate` | Compare approaches |
| `gcc_adopt` | Merge winning approach |
| `read_file` | Read file contents |
| `run_command` | Execute shell command |
| `write_file` | Write content to file |

## Architecture

### Graph Nodes

```
load_context        → Load L0/L1/L2 memory, check if bootstrap needed
explore_bootstrap   → On empty codebase, explore and document structure
read_roadmap        → Parse main.md, extract current todo and target files
explore_validate    → Validate roadmap (first todo only)
explore_recon       → Ground target files in actual codebase
match_rules         → Load rules matching target file paths
deepen_context      → LLM decides which L2 files to read
execute_todo        → Inner loop: LLM call → tool execution → repeat
extract_session     → Distill GCC commits into memory/decisions/rules
roadmap_done        → Handle completion (archive, next roadmap)
```

### State Flow

```python
AgentState {
    messages: list[BaseMessage]          # Conversation history
    roadmap: str                         # Raw main.md content
    current_todo: TodoItem | None        # {text, done, index}
    target_files: list[str]              # Files for current todo
    
    briefing: str                        # Explorer output
    exploration_mode: str                # "validate" | "recon"
    
    memory: AgentMemoryContext {         # Loaded context
        l0_index: str
        l1_files: dict[str, str]
        l2_files: dict[str, str]
        active_rules: dict[str, str]
        session_history: str
    }
    
    working_branch: str | None          # Git branch
    session_start_commit: int            # For extract_session
    
    todos_completed_this_session: list[str]
}
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# With coverage
pytest --cov=sebba_code

# Type checking (if configured)
mypy src/sebba_code/
```

## Project Structure

```
sebba_code/
├── __init__.py              # Package entry, version
├── __main__.py              # CLI entry point
├── cli.py                   # Click CLI commands
├── config.py                # Configuration loading
├── constants.py             # Agent directory paths
├── graph.py                 # Main LangGraph assembly
├── llm.py                   # LLM provider configuration
├── prompts.py               # System prompt building
├── seed.py                  # Roadmap initialization
├── state.py                 # AgentState TypedDict
│
├── nodes/                   # Graph nodes
│   ├── context.py           # deepen_context
│   ├── done.py              # roadmap_done
│   ├── execute.py           # execute_todo subgraph
│   ├── explore.py           # explore_bootstrap/recon/validate
│   ├── extract.py           # extract_session
│   ├── load_context.py      # load_context + needs_bootstrap
│   ├── roadmap.py           # read_roadmap + has_todo/is_first_todo
│   └── rules.py             # match_rules
│
├── tools/                   # Agent tools
│   ├── code.py              # read_file, write_file, run_command
│   ├── exploration.py       # gcc_explore, gcc_try_approach, gcc_evaluate, gcc_adopt
│   ├── memory.py            # memory_query
│   └── progress.py          # gcc_commit, mark_todo_done, add_todo, discover_files
│
└── helpers/                 # Utilities
    ├── files.py             # File operations
    ├── git.py               # Git subprocess wrappers
    ├── markdown.py          # Markdown manipulation
    ├── memory_ops.py        # Memory file updates
    ├── parsing.py           # JSON extraction
    └── rules_ops.py         # Rules processing
```

## Dependencies

- **langgraph** >= 0.4 — Graph-based agent framework
- **langchain-core** >= 0.3 — LLM abstractions
- **langchain-anthropic** >= 0.3 — Claude integration
- **langchain-openai** >= 0.3 — OpenAI integration
- **langchain** >= 0.3 — Chain utilities
- **pyyaml** >= 6.0 — Config parsing
- **click** >= 8.0 — CLI framework

## Design Influences

- **GCC paper** — commit/branch/merge context protocol
- **OpenViking** — tiered L0/L1/L2 memory loading
- **Claude Code** — path-scoped rules in `.claude/rules/`
- **Beads** — git-native task tracking

## License

See project repository for license information.
