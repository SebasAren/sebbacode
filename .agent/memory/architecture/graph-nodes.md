# Graph Node Wiring Pattern

## Adding a New Node to the Graph

1. Create node file at `src/sebba_code/nodes/{name}.py` with `node_function(state) -> state`
2. Define any new TypedDict fields in `state.py` if node produces new state data
3. Add node to `graph.py` and wire as synchronous downstream

## Synchronous Downstream Wiring

When a node must run immediately after another (tight coupling, shared state), wire it as synchronous downstream:

```python
# Instead of async hook pattern:
# extract_session.add_edge(...)

# Use synchronous downstream:
execute_subgraph.add_node(PlanningNode(summarize_to_l1, ...))
execute_subgraph.add_edge("extract_session", "summarize_to_l1")
```

**Choice criteria**:
- Synchronous: nodes share state, must run sequentially, tight coupling
- Async hook: independent timing, loose coupling, event-driven triggers

## Node Return Values

Nodes can return dicts that get merged into state:
```python
# In node:
return {"l2_entries": entries, "l1_summary": summary}

# Graph handles merge into TypedDict state
```
