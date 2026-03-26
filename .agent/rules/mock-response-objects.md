---
paths:
  - "tests/**/*.py"
---
When mocking LLM chain calls (especially `invoke_with_timeout`), the mock must return complete response objects with all required fields. Returning None causes silent failures. Configure fixtures in conftest.py to return properly typed objects (e.g., L1Summary with file, topic, summary fields).