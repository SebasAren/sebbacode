## draft_roadmap Node

**Purpose**: Generates initial roadmap drafts from user requests + memory context (L0/L1/L2)
**Location**: `src/sebba_code/nodes/planning.py`
**Pattern**: Uses existing LLM client pattern from codebase
**Output**: Writes draft to state (not disk)
**Context inputs**: user_request, loaded L0 memory, git state, codebase structure