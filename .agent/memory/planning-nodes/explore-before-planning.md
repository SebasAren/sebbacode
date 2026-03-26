## Explore Before Planning Directive

### Directive Purpose
A new directive was added to the `draft_plan_prompt` within `src/sebba_code/planning_prompts.py` to enforce a strict tool usage order: the planner MUST call the explore tool directly BEFORE creating subagent tasks.

### Implementation Details
- **Location**: `src/sebba_code/planning_prompts.py` - modified `draft_plan_prompt`
- **Insertions**: 6 lines added to enforce directive
- **Format**: Added as a directive statement instructing the planner to prioritize exploration

### Reason for Implementation
- **Problem**: Previous planning nodes could create subagent tasks with insufficient context, leading to disconnected or redundant tasks
- **Solution**: Force exploration of relevant code structure, tool implementations, and existing patterns before task creation
- **Order Enforced**: explore_tool → create_subagent_tasks

### Benefits
1. **Better Context Gathering**: Planner now examines actual code structure before generating tasks
2. **Tool Discovery**: Ensures relevant tools (like `execute`, `git`, `http`) are explored before task planning
3. **Reduced Redundancy**: Prevents creating tasks for features that already exist or use patterns already identified
4. **Improved Task Quality**: Subagent tasks are based on concrete exploration findings rather than assumptions

### Integration with Existing Flow
- This directive complements the existing `planning_iteration` cycle (draft_roadmap → critique_roadmap → refine_roadmap → write_roadmap)
- Exploration occurs during the initial `draft_roadmap` phase before critique/refine steps
- Maintains compatibility with existing memory context (L0/L1/L2) already built into the node

### Verification
- Commit message format corrected to conventional commit standards
- Changes verified in draft_plan_prompt with 6 targeted insertions
- No conflicts with existing TypedDict state requirements or graph wiring patterns