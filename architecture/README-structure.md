# README Structure Guidelines

This document defines the required and optional sections for the project README, along with anti-patterns to avoid.

## Required Sections (in order)

### 1. Title & Tagline
One-line project name with a brief description of what it does.

### 2. Architecture
High-level overview of the system design:
- Graph-based architecture (LangGraph state machine)
- DAG-based parallel execution
- Tiered memory system (L0/L1/L2)
- Task worker subgraph

### 3. Installation
How to install and set up the project:
- Package manager commands (uv recommended)
- Python version requirement
- Any environment setup required

### 4. CLI Reference
Complete reference of all CLI commands and flags:
- Every command in cli.py must be documented
- Every flag/option must be documented
- Include short description for each

### 5. Quick Start
Getting started example with basic usage flow.

### 6. Configuration
Configuration file format and environment variables:
- Show config.yaml structure
- List all environment variables
- Explain precedence (config > env > defaults)

### 7. Memory Architecture
Details of the tiered memory system (L0/L1/L2).

### 8. Rules System
How path-scoped rules work.

## Optional Sections

- Roadmap Format (documentation of file formats)
- Session Summaries (example of output)
- Contributing (or link to CONTRIBUTING.md)
- Project Structure
- Dependencies
- Design Influences
- License

## Anti-Patterns (Must Avoid)

### 1. No Hardcoded Secrets
**NEVER** include real or example API keys, tokens, or secrets in any format:
```bash
# BAD - placeholder shown as real
export SEBBA_API_KEY="sk-ant-..."
```
Use clearly marked placeholders: `export SEBBA_API_KEY="your-api-key-here"` or document-only.

### 2. No Placeholder Text
Do not include `[TODO]`, `[FIXME]`, `[INSERT_X_HERE]` blocks in documentation.

### 3. No Stale Information
When source code changes, update documentation within the same PR/commit.

### 4. No Missing Commands
Every command and flag in `cli.py` MUST appear in the CLI Reference section.

## README Maintenance Pattern

When adding features or making architectural changes:

1. **Review recent commits** to identify all changes
2. **Audit README against codebase** to list discrepancies before making changes
3. **Prioritize audit before update** to ensure complete coverage
4. **Update feature descriptions** with current command syntax and functionality
5. **Refresh usage examples** to match actual behavior
6. **Run pytest** to verify documentation changes didn't break anything

## Discrepancy Checklist

When auditing README.md, verify:

| Item | Status | Notes |
|------|--------|-------|
| All CLI commands documented | Required | Check `cli.py` for complete list |
| All CLI flags documented | Required | Include defaults |
| Environment variables match config.py | Required | Check `config.py` for env vars |
| `--max-todos` flag removed (if not implemented) | Required | Must match actual CLI |
| No hardcoded secrets | Required | Use placeholder format |
| Architecture matches graph.py | Required | 12-node graph |
| Memory tiers match actual implementation | Required | L0/L1/L2 loading |
| Node names match source | Required | planning, dispatch, worker, etc. |

## Validation

Run this check before committing README changes:

```bash
# Verify no hardcoded API keys
grep -n "sk-ant-\|sk-\|ghp_\|Bearer" README.md && echo "FAIL: secrets found"

# Verify CLI commands match
python -c "from sebba_code.cli import cli; print([c.name for c in cli.commands.values()])"
```
