---
paths:
  - "tests/**/*.py"
---
# Testing Mock Rules

## Patch Targets
When mocking functions imported via `from X import Y`, always patch at the **usage site** (`module_that_imports.Y`), not the definition site (`X.Y`). The `from` import creates a local binding that `unittest.mock.patch` on the original module will not intercept.

For memory summarization pipeline specifically: patch `sebba_code.memory.summarize.invoke_with_timeout` and `sebba_code.memory.summarize.get_cheap_llm`, not `sebba_code.llm.*`.

## Mock Response Requirements
- Mocks of `invoke_with_timeout` MUST have `.content` with ≥10 words and ≥40 chars to pass `_is_valid_summary` validation — otherwise the retry loop fires with exponential-backoff sleeps
- Return complete typed response objects with all required fields — never `None`
- For LLM chain mocks: include proper `AIMessage` structure or equivalent typed objects
- For tool call mocks: provide full `tool_calls` list with proper `id`, `name`, `args`
- Configure fixtures in `conftest.py` to return properly typed objects (e.g., `L1Summary` with file, topic, summary fields)

## Config Testing
Test configuration options via environment variable manipulation (`monkeypatch`/`os.environ`) to verify real-world override behavior, not just defaults.

## Import Verification
Before running pytest, verify that imports succeed. `importing.py` must work before pytest can collect tests. If tests fail on import: check for circular imports or missing `__init__.py`.
