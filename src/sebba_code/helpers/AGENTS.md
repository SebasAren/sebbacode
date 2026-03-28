# Helper Utilities

**Parent:** `AGENTS.md` (root)
**Score:** 8 — utility domain

## OVERVIEW
Cross-cutting utilities for git operations, markdown manipulation, file utilities, parsing, and rules processing.

## STRUCTURE
```
helpers/
├── __init__.py       # Public API exports
├── files.py          # is_relevant, list_available_files, summarize_memory_files, summarize_rules
├── git.py            # git_run, get_current_branch
├── git_commit.py     # ConventionalCommit, make_commit, COMMIT_TYPES
├── markdown.py       # append_to_section, replace_section, summarise_file
├── parsing.py        # format_dict, parse_json, parse_json_list
└── rules_ops.py      # parse_path_frontmatter, strip_frontmatter, find_nearest_agent_dir
```

## PUBLIC API

```python
# File utilities
is_relevant(path, query) → bool                    # Relevance scoring
list_available_files(agent_dir) → list[Path]        # Memory files listing
summarize_memory_files(paths) → str                 # Memory file summaries
summarize_rules(paths) → str                        # Rules content summary

# Git utilities
git_run(args, cwd) → subprocess.CompletedProcess    # Safe git wrapper
get_current_branch() → str                          # Current branch name

# Commit utilities
make_commit(message) → str                         # Create conventional commit
COMMIT_TYPES = ["feat", "fix", "docs", "refactor", "test", "chore"]

# Markdown utilities
append_to_section(path, section, content)           # Append to section
replace_section(path, section, old, new)            # Replace section content
summarise_file(path, max_chars) → str                # Truncate with summary

# Parsing utilities
parse_json(text) → dict | None                       # Safe JSON parsing
parse_json_list(text) → list | None                 # JSON array parsing
format_dict(data) → str                             # Pretty-print dict

# Rules utilities
parse_path_frontmatter(content) → tuple[dict, str]  # Extract YAML frontmatter
strip_frontmatter(content) → str                   # Remove frontmatter
find_nearest_agent_dir(start_path) → Path           # Walk up for .agent/
```

## CONVENTIONS

- All functions are pure or have clear side effects documented
- Git operations use `git_run` wrapper for consistent error handling
- Markdown operations work with section markers (`## Section Name`)
- Rules files use YAML frontmatter with `paths:` glob array

## KEY PATTERNS

```python
# Rules frontmatter format
---
paths:
  - "**/*.test.ts"
  - "**/*.spec.ts"
---
# Rule content here

# Section-based markdown
## Section Name
content

# Conventional commit format
type(scope): description
feat(auth): add JWT support
```

## NOTES

- `rules_ops.py` parses path-scoped rules from `.agent/rules/*.md`
- `find_nearest_agent_dir` walks up directory tree to locate `.agent/`
- `git_commit.py` provides `ConventionalCommit` Pydantic model
- Tests use `_task()` factory pattern in `test_dispatch.py`
