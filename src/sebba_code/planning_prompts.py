"""Planning prompt templates for draft, critique, and refine stages."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sebba_code.state import AgentState

# Maximum characters for each context section to prevent token overflow
MAX_L0_CHARS = 2000
MAX_RULES_CHARS = 1500
MAX_L1_CHARS = 800
MAX_BRIEFING_CHARS = 2000
MAX_DRAFT_CHARS = 3000
MAX_CRITERIA_CHARS = 1500


def _truncate(text: str, max_chars: int, suffix: str = "...") -> str:
    """Truncate text to max_chars, adding suffix if truncated."""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - len(suffix)] + suffix


def _format_todo_checklist() -> str:
    """Return the expected todo format for reference."""
    return """- [ ] Todo item description (start with action verb, be specific)
- [ ] Another todo item"""


def draft_roadmap_prompt(state: "AgentState", context: dict | None = None) -> str:
    """Generate the prompt for creating an initial roadmap draft.

    Args:
        state: The current agent state containing user_request, memory, and briefing
        context: Optional additional context dict (git state, file structure)

    Returns:
        A formatted prompt string for the LLM to generate a roadmap draft.
    """
    user_request = state.get("user_request", "")
    memory = state.get("memory", {})
    briefing = state.get("briefing", "")

    # Assemble context from memory with truncation
    memory_sections = []

    # L0 index - project overview
    l0_index = memory.get("l0_index", "")
    if l0_index:
        memory_sections.append(
            f"# Project Overview\n{_truncate(l0_index, MAX_L0_CHARS)}"
        )

    # Active rules - constraints that must be followed
    active_rules = memory.get("active_rules", {})
    if active_rules:
        rules_text = "\n\n".join(f"## {name}\n{content}" for name, content in active_rules.items())
        memory_sections.append(f"# Active Rules (MUST follow)\n{_truncate(rules_text, MAX_RULES_CHARS)}")

    # L1 files - relevant context files
    l1_files = memory.get("l1_files", {})
    if l1_files:
        l1_texts = [f"## {name}\n{_truncate(content, MAX_L1_CHARS)}" for name, content in l1_files.items()]
        memory_sections.append("# Relevant Context\n" + "\n\n".join(l1_texts))

    # Additional context from exploration
    if context:
        git_state = context.get("git_state", "")
        file_structure = context.get("file_structure", "")
        if git_state:
            memory_sections.append(f"# Git State\n{git_state}")
        if file_structure:
            memory_sections.append(f"# File Structure\n{file_structure}")

    # Briefing from codebase exploration (if available)
    briefing_section = ""
    if briefing:
        briefing_section = f"# Codebase Briefing\n{_truncate(briefing, MAX_BRIEFING_CHARS)}\n\n"

    memory_context = "\n\n---\n\n".join(memory_sections) if memory_sections else "(No prior context available)"

    prompt = f"""You are creating a roadmap to guide implementation of a new feature or task.

## User Request
{user_request}

{briefing_section}# Memory Context
{memory_context}

---

# Roadmap Format

Generate a markdown document with **exactly** these sections:

## Goal
One paragraph describing the overall objective and success criteria.

## Context
Explain where this request came from, what problem it solves, and the current state of the codebase relevant to this work.

## Todos
Ordered, actionable steps that are:
- Concrete and specific (not vague)
- Completable in one session (1-4 hours each)
- Written as imperatives starting with action verbs
- Properly ordered with dependencies first

Example format:
{_format_todo_checklist()}

## Target Files
List of files to create or modify, with brief purpose for each.

## Active Branches
List any branches to be created or used (start empty if none planned).

## Decisions Made
Key architectural or design decisions made during planning.

## Constraints
Non-functional requirements and things to preserve (backward compatibility, performance, etc.).

---

# Guidelines

1. Keep todos focused on the user's request - avoid scope creep
2. Use concrete, specific language - "Add X to Y" not "Improve Y"
3. Ensure proper dependency ordering - foundation tasks before dependent tasks
4. Limit todos to 5-8 items - prefer fewer, larger todos over many small ones
5. Reference existing patterns in the codebase where applicable

Generate your roadmap now.
"""
    return prompt


def critique_roadmap_prompt(state: "AgentState", draft: str | None = None) -> str:
    """Generate the prompt for critiquing a roadmap draft.

    Uses the CHEAP model (Haiku). Output must be parseable.

    Args:
        state: The current agent state
        draft: Optional draft roadmap to critique (falls back to state['draft_roadmap'])

    Returns:
        A formatted prompt string for the LLM to validate the roadmap.
    """
    if draft is None:
        draft = state.get("draft_roadmap", "")

    user_request = state.get("user_request", "")
    memory = state.get("memory", {})
    briefing = state.get("briefing", "")

    # Brief context for validation
    l0_index = _truncate(memory.get("l0_index", ""), 500, "")
    active_rules = memory.get("active_rules", {})
    rules_brief = ""
    if active_rules:
        rules_list = ", ".join(active_rules.keys())
        rules_brief = f" (MUST respect: {rules_list})"

    briefing_brief = _truncate(briefing, 500, "") if briefing else ""

    prompt = f"""You are validating a roadmap draft for the following request:
**{user_request}**

Context: {l0_index or '(none)'}
Rules to follow: {rules_brief or '(none)'}
Briefing: {briefing_brief or '(none)'}

---

## Draft Roadmap Under Review

{draft}

---

## Validation Checklist

Critique the roadmap against these criteria. Be concise and specific.

### Format Validation
- [ ] Contains "## Goal" section
- [ ] Contains "## Todos" section with checkboxes (- [ ] or - [x])
- [ ] Contains "## Target Files" section
- [ ] Uses consistent markdown formatting

### Content Validation
- [ ] Todos are specific and actionable (not vague)
- [ ] Todos are ordered with dependencies first
- [ ] No more than 8 todos (prevents scope creep)
- [ ] Target files are realistic for the scope
- [ ] No major features missing from todos

### Scope Validation
- [ ] Todos align with the user request
- [ ] No obvious scope creep (unrequested features)
- [ ] Scope is achievable in reasonable time

---

## Output Format

Provide your critique in this exact format:

### Issues Found
(List specific issues, or write "None" if the roadmap is acceptable)

### Severity
- **blocking**: Must fix before proceeding (e.g., missing sections, wrong format)
- **warning**: Should fix (e.g., vague todos, minor issues)
- **suggestion**: Nice to have (e.g., better ordering, clearer wording)

### Suggested Fixes
(Numbered list of concrete fixes for each blocking/warning issue)

### Verdict
**APPROVED** - Roadmap is ready
**NEEDS_WORK** - Roadmap has blocking or warning issues

---

Use your analysis to provide actionable feedback. Focus on blocking issues first.
"""
    return prompt


def refine_roadmap_prompt(state: "AgentState", draft: str | None = None, critique: str | None = None) -> str:
    """Generate the prompt for refining a roadmap based on critique.

    Args:
        state: The current agent state
        draft: The draft roadmap to refine (falls back to state['draft_roadmap'])
        critique: The critique to address (falls back to state['critique'])

    Returns:
        A formatted prompt string for the LLM to refine the roadmap.
    """
    if draft is None:
        draft = state.get("draft_roadmap", "")

    if critique is None:
        critique = state.get("critique", "")

    user_request = state.get("user_request", "")
    planning_iteration = state.get("planning_iteration", 1)
    memory = state.get("memory", {})

    # Get context for reference
    l0_index = _truncate(memory.get("l0_index", ""), MAX_L0_CHARS)
    active_rules = memory.get("active_rules", {})
    rules_text = ""
    if active_rules:
        rules_text = "\n\n".join(f"## {name}\n{content}" for name, content in active_rules.items())
        rules_text = _truncate(rules_text, MAX_RULES_CHARS)

    prompt = f"""You are refining a roadmap draft based on critique feedback.

## Original Request
{user_request}

## Planning Context
- Iteration: {planning_iteration} of ~3 (this is iteration {planning_iteration})
- Project Overview: {l0_index or '(none)'}

{('## Active Rules\n' + rules_text) if rules_text else ''}

---

## Current Draft Roadmap

{draft}

---

## Critique Feedback to Address

{critique if critique else '(No specific critique provided - apply general improvements)'}

---

## Refinement Instructions

1. Address all **blocking** issues from the critique first
2. Address **warning** issues where straightforward
3. Ignore minor **suggestion** issues if complex
4. Maintain the roadmap format (Goal, Context, Todos, Target Files, etc.)
5. Keep todo format as checkboxes: - [ ]
6. Ensure proper todo ordering with dependencies first

## Output Format

Provide ONLY the refined roadmap in markdown format. Start directly with "## Goal" - do not include preamble or explanation.

Your refined roadmap:
"""
    return prompt


def format_validation_prompt() -> str:
    """Return a regex-friendly format specification for validation.

    Used by nodes to verify roadmap format matches read_roadmap expectations.
    """
    return """
# Expected Roadmap Format

## Goal
[One paragraph]

## Context
[Background and problem description]

## Todos
- [ ] [Specific todo item]
- [ ] [Another specific todo item]

## Target Files
- [file path]: [brief purpose]

## Active Branches
- [branch name] (or empty)

## Decisions Made
- [decision] (or empty)

## Constraints
- [constraint] (or empty)
"""
