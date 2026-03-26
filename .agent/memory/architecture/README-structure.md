README reorganization order: Architecture (Graph Flow, Tiered Memory, Execute Subgraph) → Installation → CLI Reference. Execute Subgraph is a third Architecture subsection.
## README Maintenance Pattern

When adding features or making architectural changes:
1. Review commits with `git log` to identify recent changes
2. Compare README against actual source files in `nodes/`, `cli.py`, and tool implementations
3. Audit for undocumented features: worktree exploration, new tools, architecture changes, dependencies
4. README should document: LangGraph architecture, Python-only requirement, available todo/roadmap tools

Major discrepancies to flag: new features, architecture shifts (e.g., GCC → LangGraph), missing dependencies, tool availability.

## ## README Maintenance Pattern
## README Maintenance Pattern

When adding features or making architectural changes:
1. **Review recent commits** to identify all changes since last update
2. **Audit README against codebase** to list discrepancies before making changes
3. **Prioritize audit before update** to ensure complete coverage of all changes
4. **Update feature descriptions** with current command syntax and new functionality
5. **Refresh usage examples** to match actual behavior
6. **Run pytest** to verify documentation changes didn't break anything

**Task completion heuristic**: If the actual work is the audit/refresh phase, the parent task can be marked auto-completed since discrepancies were identified and addressed.
## README Maintenance Pattern

### How to Audit README Against Codebase

When README falls out of sync with implementation:

1. **Compare with git commits** - Review recent commits to understand what changed
2. **Read source files** - Key files to audit: nodes/__init__.py, nodes/rules.py, nodes/execute.py, nodes/extract.py, CLI module, todo tools, exploration tools, constants
3. **Focus on structural discrepancies, not formatting**
   - Missing `.agent/` directory documentation
   - Undocumented features (e.g., todo management, exploration tools)
   - Features that exist in code but not in README
4. **Audit approach** - List all discrepancies, prioritize by impact
## README Maintenance Pattern
When adding features or making architectural changes:
1. Review recent git commits to identify all changes
2. Read README.md to assess current documentation state
3. Examine source files to understand actual implementation
4. Perform comprehensive README vs codebase audit
5. Identify all discrepancies between documented and actual implementation
6. Track discrepancies and address in update phase

**Major discrepancy categories**: new features/commands, removed features, architectural refactors (e.g., LangGraph state replacement of file-based state)
### Phase Tracking Lesson
Mark audit/identification todos complete only when that phase is done. Clearly separate 'identify discrepancies' from 'implement fixes'. In this session, 'update feature descriptions' was incorrectly marked complete when only the audit was finished.