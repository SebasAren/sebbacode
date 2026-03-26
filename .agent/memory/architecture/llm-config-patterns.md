# LLM Configuration Patterns

## Cheap Model Selection for L2→L1 Summarization

Use `_get_` prefixed functions for model configuration helpers:

```python
def _get_cheap_model() -> str:
    """Get cheap model for lightweight operations (critique, summarization)."""
    return os.getenv('SEBBA_CHEAP_MODEL', DEFAULT_CHEAP_MODEL)

def _get_model() -> str:
    """Get primary model for generation tasks."""
    return os.getenv('SEBBA_MODEL', DEFAULT_MODEL)
```

**Pattern**: Default behavior unchanged when no custom config provided. Environment variables tested directly in unit tests via `monkeypatch`.

**Use cases**: Critique nodes, L2→L1 summarization, validation steps—anywhere a less capable but cheaper model suffices.
