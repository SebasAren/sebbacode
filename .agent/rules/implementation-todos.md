---
paths:
  - "src/sebba_code/**"
---
When implementing features referenced in toodos, the todo TITLE takes priority over DESCRIPTION text when there are discrepancies. Example: todo titled 'draft_roadmap' with description mentioning 'critique_roadmap' → implement as draft_roadmap node. This ensures consistency across the codebase. When mocking functions imported via 'from X import Y', always patch at usage site (module_that_imports.Y), not at definition site (module.X.Y). This prevents scope confusion in test isolation.