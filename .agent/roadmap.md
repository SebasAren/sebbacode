## Goal
Update the project README documentation to accurately reflect recent code changes, ensuring users and contributors have current, accurate information about the project's functionality, setup instructions, and usage.

## Context
Recent changes have been merged into the codebase, but the README has not been updated to reflect these modifications. This creates a documentation gap where the main entry point for new users and contributors no longer matches the current state of the project. Outdated documentation can lead to confusion, failed setups, and increased support burden.

## Todos
- [x] ~~Review recent commits and changes to identify all updates needed~~
- [x] ~~Audit current README against codebase to list discrepancies~~
- [x] ~~Update installation/setup instructions if dependencies or steps changed~~
- [x] ~~Update feature descriptions if new functionality was added or modified~~
- [x] ~~Refresh usage examples or add new ones for new features~~
- [ ] Update any outdated screenshots, diagrams, or links
- [ ] Review README formatting for consistency and readability
- [ ] Proofread final document for grammar and clarity

- [x] ~~Audit README against codebase - list all discrepancies~~ → Completed full audit: removed GCC references, added planning mode docs, updated tool names, relocated roadmap path, updated config schema, added sessions/branches/worktrees architecture
## Target Files
- `README.md` — Main project documentation requiring updates

## Active Branches
- `docs/update-readme` (create new branch for documentation changes)

## Decisions Made
- Will maintain existing README structure to avoid breaking external links or community expectations
- Changes will be organized by section (Features, Installation, Usage, etc.) for easy review
- If major changes occurred, consider adding a "Recent Changes" or "Changelog" section

## Constraints
- Preserve existing README formatting and style for consistency
- Ensure any new commands or configurations are tested before documenting
- Maintain any badges (CI status, version, etc.) that should remain unchanged
- Do not introduce breaking changes to documentation structure that could break downstream consumers
- Constraints about 'preserving existing formatting' and 'not breaking downstream consumers' are irrelevant
- Remove 'Maintain any badges' constraint