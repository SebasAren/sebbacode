# CLI to State Flow Pattern

## Pattern: CLI Args → initial_state → Graph State

CLI arguments that affect agent behavior should flow through the initial_state dict into the graph state, rather than using a separate config object. This keeps all runtime configuration in one place.

### Implementation Pattern
```python
# cli.py - Only set when explicitly provided
initial_state = {
    "messages": [],
    # ...
}
if max_todos is not None:
    initial_state["max_todos"] = max_todos

# state.py - TypedDict with Optional for sentinel
class AgentState(TypedDict):
    max_todos: Optional[int]  # None = use default

# nodes/extract.py - Fallback pattern
max_todos = state.get("max_todos") or DEFAULT_MAX_TODOS
```

### When to Use
- CLI flags that override session limits
- Configuration affecting should_continue logic
- Any runtime constraint set at startup

### Anti-Pattern
- Don't create separate config objects outside graph state
- Don't populate state with default values when not needed