
## Optional[T] as Sentinel for Defaults

Use `Optional[T]` fields in TypedDict where `None` means "apply default". This avoids needing separate `has_` boolean flags.

```python
# Good
max_todos: Optional[int]  # None → use DEFAULT_MAX_TODOS

# Avoid
max_todos_set: bool
max_todos_value: int
```