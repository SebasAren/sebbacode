# README Audit Checklist

## Audit Phase
1. Identify recent commits: `git log --oneline -10`
2. List files touched in those commits
3. Read source files (not just diffs) for complete understanding
4. Cross-reference against README.md
5. Flag discrepancies by severity: HIGH/MEDIUM/LOW

## Discrepancy Types
- **HIGH**: Missing features entirely (worktree, LangGraph, Python-only)
- **MEDIUM**: Renamed/changed behavior not documented (tool renames)
- **LOW**: Removed features still mentioned (GCC removal)

## Principles
- Focus on code-to-docs discrepancies, not formatting/style
- Track audit vs fix phases separately - don't mark complete when only audited
- Use severity + fix effort for remediation planning

## Specific Audits Completed
- Commits 4e61496, 76edb05, 8cb9964: Missing docs for worktree, LangGraph, Python-only mode, tools module