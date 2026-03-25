"""Implements the exploration nodes for codebase bootstrapping, validation, and reconnaissance."""

import logging
import subprocess
from pathlib import Path

from sebba_code.constants import DEBUG_PROMPTS, get_agent_dir
from sebba_code.helpers.files import list_available_files
from sebba_code.helpers.markdown import append_to_section, replace_section, summarise_file
from sebba_code.helpers.parsing import format_dict, parse_json
from sebba_code.llm import get_llm
from sebba_code.state import AgentState

logger = logging.getLogger("sebba_code")


def explore_bootstrap(state: AgentState) -> dict:
    """Scan entire repo and build initial memory. Runs once on first use."""
    logger.info("explore: bootstrap — scanning repo")
    agent_dir = get_agent_dir()

    # Gather repo structure
    tree_output = subprocess.run(
        [
            "find",
            ".",
            "-maxdepth",
            "3",
            "-not",
            "-path",
            "./.git/*",
            "-not",
            "-path",
            "*/node_modules/*",
        ],
        capture_output=True,
        text=True,
    ).stdout

    # Read key config files
    config_files = {}
    for pattern in [
        "package.json",
        "*/package.json",
        "tsconfig.json",
        "*/tsconfig.json",
        ".gitlab-ci.yml",
        "Dockerfile",
        "*/Dockerfile",
        ".eslintrc*",
        ".prettierrc*",
        ".editorconfig",
        "README.md",
        "CONTRIBUTING.md",
        "vitest.config.*",
        "jest.config.*",
        "pyproject.toml",
        "*/pyproject.toml",
        "requirements*.txt",
    ]:
        for f in Path(".").glob(pattern):
            if "node_modules" not in str(f):
                try:
                    config_files[str(f)] = f.read_text()[:2000]
                except Exception:
                    pass

    bootstrap_prompt = f"""You are exploring a codebase for the first time.
Build a complete understanding and generate memory files.

## Directory Structure
{tree_output[:3000]}

## Config Files
{format_dict(config_files)}

Generate a JSON object:
{{
  "index_md": "Content for _index.md — one-line summaries per area",
  "architecture_md": "Content for architecture.md — L1 system overview",
  "conventions_md": "Content for conventions.md — L1 coding conventions",
  "l2_files": [
    {{"path": "architecture/some-domain.md", "content": "Deep detail"}}
  ],
  "inferred_rules": [
    {{"file": "rules/rule-name.md", "paths": ["glob"] | null, "content": "Rule text"}}
  ]
}}
"""

    llm = get_llm()
    if DEBUG_PROMPTS:
        logger.debug("── bootstrap prompt (%d chars) ──\n%s", len(bootstrap_prompt), bootstrap_prompt[:2000])
    response = llm.invoke(bootstrap_prompt)
    result = parse_json(response.content)

    # Write memory files
    memory_dir = agent_dir / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    (memory_dir / "_index.md").write_text(result["index_md"])
    (memory_dir / "architecture.md").write_text(result["architecture_md"])
    (memory_dir / "conventions.md").write_text(result["conventions_md"])

    for l2 in result.get("l2_files", []):
        path = memory_dir / l2["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(l2["content"])

    # Write inferred rules
    for rule in result.get("inferred_rules", []):
        rule_path = agent_dir / rule["file"]
        rule_path.parent.mkdir(parents=True, exist_ok=True)
        content = ""
        if rule.get("paths"):
            content = "---\npaths:\n"
            for p in rule["paths"]:
                content += f'  - "{p}"\n'
            content += "---\n"
        content += rule["content"]
        rule_path.write_text(content)

    return {
        "memory": {**state["memory"], "l0_index": result["index_md"]},
        "exploration_mode": "bootstrap",
    }


def explore_validate(state: AgentState) -> dict:
    """Validate a freshly seeded roadmap against the actual codebase."""
    logger.info("explore: validate — checking roadmap against codebase")
    agent_dir = get_agent_dir()
    roadmap = state["roadmap"]
    target_files = state["target_files"]

    # Check which target files exist and read them
    file_status = {}
    for f in target_files:
        path = Path(f)
        if path.exists():
            content = path.read_text()
            file_status[f] = {
                "exists": True,
                "lines": len(content.split("\n")),
                "preview": "\n".join(content.split("\n")[:50]),
            }
        else:
            file_status[f] = {
                "exists": False,
                "parent_exists": path.parent.exists(),
            }

    # Trace imports from existing target files
    imports_found = {}
    for f, status in file_status.items():
        if status.get("exists") and f.endswith((".ts", ".js", ".tsx", ".jsx", ".py")):
            result = subprocess.run(
                ["grep", "-n", r"^import\|^from", f],
                capture_output=True,
                text=True,
            )
            if result.stdout:
                imports_found[f] = result.stdout

    validate_prompt = f"""Validate this roadmap against the actual codebase.

## Roadmap
{roadmap}

## Target File Status
{format_dict(file_status)}

## Imports Found
{format_dict(imports_found)}

Produce JSON:
{{
  "corrections": [
    {{"type": "fix_path|add_file|add_todo|add_constraint|refine_todo", "detail": "...", "reason": "..."}}
  ],
  "updated_target_files": ["corrected/list"],
  "warnings": ["things to watch out for"],
  "briefing": "Summary of codebase state relevant to this roadmap"
}}

Only flag real problems, not theoretical ones.
"""

    llm = get_llm()
    if DEBUG_PROMPTS:
        logger.debug("── validate prompt (%d chars) ──\n%s", len(validate_prompt), validate_prompt[:2000])
    response = llm.invoke(validate_prompt)
    result = parse_json(response.content)

    # Apply corrections to main.md
    main_md = agent_dir / "gcc" / "main.md"
    content = main_md.read_text()

    for correction in result.get("corrections", []):
        if correction["type"] == "add_todo":
            content = append_to_section(
                content, "## Todos", f"- [ ] {correction['detail']}"
            )
        elif correction["type"] == "add_constraint":
            content = append_to_section(
                content, "## Constraints", f"- {correction['detail']}"
            )

    if result.get("updated_target_files"):
        content = replace_section(
            content,
            "## Target Files",
            "\n".join(f"- {f}" for f in result["updated_target_files"]),
        )

    main_md.write_text(content)

    return {
        "roadmap": main_md.read_text(),
        "target_files": result.get("updated_target_files", target_files),
        "briefing": result.get("briefing", ""),
        "exploration_mode": "validate",
    }


def explore_recon(state: AgentState) -> dict:
    """Per-todo reconnaissance. Build a briefing for the executor."""
    logger.info("explore: recon — building briefing for todo")
    todo = state["current_todo"]
    target_files = state["target_files"]

    # Read target files
    file_contents = {}
    for f in target_files:
        path = Path(f)
        if path.exists():
            content = path.read_text()
            if len(content) > 3000:
                file_contents[f] = summarise_file(f, content)
            else:
                file_contents[f] = content
        else:
            file_contents[f] = "(does not exist yet)"

    # Trace imports one level deep
    dependency_map = {}
    for f in target_files:
        if Path(f).exists() and f.endswith((".ts", ".js", ".tsx", ".jsx", ".py")):
            result = subprocess.run(
                ["grep", "-E", r"^(import|export.*from|from .* import)", f],
                capture_output=True,
                text=True,
            )
            if result.stdout.strip():
                dependency_map[f] = result.stdout.strip()

    # Find related test files
    test_files = {}
    for f in target_files:
        stem = Path(f).stem
        for pattern in [f"**/{stem}.test.ts", f"**/{stem}.spec.ts", f"**/{stem}_test.py", f"**/test_{stem}.py"]:
            for test_file in Path(".").glob(pattern):
                test_files[str(test_file)] = test_file.read_text()[:1000]

    # Recent git history
    git_history = ""
    for f in target_files[:5]:
        if Path(f).exists():
            log = subprocess.run(
                ["git", "log", "--oneline", "-5", "--", f],
                capture_output=True,
                text=True,
            ).stdout
            if log:
                git_history += f"\n### {f}\n{log}"

    recon_prompt = f"""Build a briefing for this coding task.

## Todo: {todo["text"]}
## Roadmap Context
{state["roadmap"]}

## Target Files
{format_dict(file_contents)}

## Dependencies (imports)
{format_dict(dependency_map)}

## Related Tests
{format_dict(test_files) if test_files else "None found."}

## Recent Git History
{git_history or "No recent changes."}

Write a concise, actionable briefing covering:
1. Current State — what exists, what needs creating
2. Dependencies — what this touches beyond target files
3. Patterns to Follow — code patterns from existing files
4. Existing Tests — what's covered, what's missing
5. Risks — things that could go wrong
"""

    llm = get_llm()
    if DEBUG_PROMPTS:
        logger.debug("── recon prompt (%d chars) ──\n%s", len(recon_prompt), recon_prompt[:2000])
    response = llm.invoke(recon_prompt)

    return {"briefing": response.content, "exploration_mode": "recon"}
