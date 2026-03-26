---
paths:
  - "tests/**/*.py"
---
When mocking functions imported via `from X import Y`, always patch at the **usage site** (`module_that_imports.Y`), not the definition site (`X.Y`). The `from` import creates a local binding that `unittest.mock.patch` on the original module will not intercept. For the memory summarization pipeline specifically: patch `sebba_code.memory.summarize.invoke_with_timeout` and `sebba_code.memory.summarize.get_cheap_llm`, not `sebba_code.llm.*`. Mock responses for `invoke_with_timeout` must have `.content` with ≥10 words and ≥40 chars to pass `_is_valid_summary` validation — otherwise the retry loop fires with exponential-backoff sleeps.
