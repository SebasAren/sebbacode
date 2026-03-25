# Contributing to sebba-code

Thank you for your interest in contributing to sebba-code! This document provides guidelines and instructions for contributing.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- pip or uv for package management
- An LLM API key (Anthropic or OpenAI)

### Setting Up Your Development Environment

```bash
# Clone the repository
git clone <repository-url>
cd sebba-code

# Install in development mode
pip install -e ".[dev]"

# Or with uv
uv pip install -e ".[dev]"

# Install additional dev dependencies
pip install pytest pytest-cov mypy

# Run tests
pytest

# Run with coverage
pytest --cov=sebba_code
```

## Development Workflow

### 1. Branch Naming

Create feature branches from `main`:

```bash
git checkout main
git pull origin main
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 2. Making Changes

When making changes:

1. Keep commits focused and atomic
2. Write clear commit messages
3. Add tests for new functionality
4. Update documentation as needed

### 3. Commit Messages

Follow conventional commits format:

```
type(scope): description

Types:
- feat: New feature
- fix: Bug fix
- docs: Documentation changes
- test: Test changes
- refactor: Code refactoring
- chore: Maintenance tasks
```

Example:
```
feat(explore): add validation for roadmap first todo
fix(cli): handle missing agent directory gracefully
docs(readme): update installation instructions
```

### 4. Testing

Run tests before submitting a PR:

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=sebba_code --cov-report=html

# Run specific test file
pytest tests/test_nodes/test_roadmap.py

# Run with verbose output
pytest -v
```

### 5. Code Quality

```bash
# Format code (if black/ruff configured)
black src/sebba_code/

# Type checking
mypy src/sebba_code/

# Linting
ruff check src/sebba_code/
```

## Pull Request Process

### Before Submitting

1. **Update tests**: Ensure all tests pass
2. **Update docs**: Update README.md if adding new features
3. **Check scope**: Keep PRs focused on a single issue/feature

### Submitting a PR

1. Push your branch to the repository
2. Open a Pull Request against `main`
3. Fill out the PR template:
   - Description of changes
   - Related issue number (if applicable)
   - Testing performed
   - Screenshots (if UI changes)

### PR Review

- PRs require at least one approval before merging
- Address review feedback by pushing additional commits
- Do not force-push to branches with open PRs

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
│   ├── context.py
│   ├── done.py
│   ├── execute.py
│   ├── explore.py
│   ├── extract.py
│   ├── load_context.py
│   ├── roadmap.py
│   └── rules.py
├── tools/              # Agent tools
│   ├── code.py
│   ├── exploration.py
│   ├── memory.py
│   └── progress.py
└── helpers/            # Utilities
    ├── files.py
    ├── git.py
    ├── markdown.py
    ├── memory_ops.py
    ├── parsing.py
    └── rules_ops.py
```

## Adding New Features

### Adding a New Node

1. Create the node file in `sebba_code/nodes/`
2. Implement the node function
3. Register the node in `sebba_code/graph.py`
4. Add tests in `tests/test_nodes/`
5. Update documentation

Example node:

```python
# sebba_code/nodes/example.py
from sebba_code.state import AgentState

def example_node(state: AgentState) -> dict:
    """Description of what this node does.
    
    Args:
        state: Current agent state
        
    Returns:
        dict: State updates to apply
    """
    # Node logic here
    return {"key": "value"}
```

### Adding a New Tool

1. Create the tool in `sebba_code/tools/`
2. Use the `@tool` decorator from langchain_core
3. Register in `sebba_code/tools/__init__.py`
4. Add tests in `tests/test_tools/`

Example tool:

```python
# sebba_code/tools/example.py
from langchain_core.tools import tool

@tool
def example_tool(param: str) -> str:
    """Description of what this tool does.
    
    Args:
        param: Description of the parameter
        
    Returns:
        Description of return value
    """
    # Tool logic here
    return "result"
```

## Reporting Issues

### Bug Reports

Include:
- sebba-code version
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error messages/logs

### Feature Requests

Include:
- Problem you're trying to solve
- Proposed solution
- Alternative solutions considered
- Any relevant context

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
