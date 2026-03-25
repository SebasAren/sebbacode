# Planning Node Architecture

## draft_roadmap Node Pattern
- Builds context dict from multiple sources: user_request, memory, git_state, codebase_structure
- Includes existing roadmap in context for re-planning scenarios
- Calls `draft_roadmap_prompt(state, context)` for prompt generation
- Invokes main LLM via `get_llm()` (creative work, not cheap model)
- Returns `{"draft_roadmap": content, "planning_iteration": 1}` on initial generation
- Draft stays in state, no disk writes

## Context Construction Pattern
```python
context = {
    "file_structure": file_structure,
    "existing_roadmap": state.get("roadmap")  # for re-planning
}
```