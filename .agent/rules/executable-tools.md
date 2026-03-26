---
paths:
  - "src/sebba_code/tools/**"
---
ALL execution tools MUST follow existing code.py pattern for architectural consistency. All execution tools use subprocess for shell execution, maintaining compatibility with existing node patterns. Node execution follows synchronous downstream pattern in graph.py with shared state, not async multi-threading for tight coupling scenarios. Orthogonal concerns separation: execution tools handle raw shell operations, nodes handle state transformations. Test execution: always verify imports succeed before running pytest to catch path issues early. For any execute/integrate operations, always run imports first before pytest execution (order matters: verify import → run pytest).