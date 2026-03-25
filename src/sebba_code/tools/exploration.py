"""Implements GCC-style exploration tools using git worktrees for parallel approach evaluation."""

import subprocess
from datetime import datetime

from langchain_core.tools import tool

from sebba_code.constants import get_agent_dir
from sebba_code.helpers.markdown import append_to_section
from sebba_code.helpers.memory_ops import remove_active_branch


@tool
def gcc_explore(question: str, approaches: list[dict]) -> str:
    """Start branching exploration with git worktrees.

    Args:
        question: The decision to explore
        approaches: List of dicts with 'name' and 'plan' keys
    """
    agent_dir = get_agent_dir()
    explore_id = f"explore-{datetime.now().strftime('%H%M%S')}"
    worktrees_dir = agent_dir / "worktrees"
    worktrees_dir.mkdir(exist_ok=True)

    results = []
    for approach in approaches:
        name = approach["name"]
        branch_name = f"gcc/{explore_id}/{name}"
        worktree_path = worktrees_dir / explore_id / name

        subprocess.run(["git", "branch", branch_name], check=True)
        subprocess.run(
            ["git", "worktree", "add", str(worktree_path), branch_name],
            check=True,
        )

        branch_dir = agent_dir / "gcc" / "branches" / f"{explore_id}-{name}"
        branch_dir.mkdir(parents=True, exist_ok=True)
        (branch_dir / "commits").mkdir(exist_ok=True)
        (branch_dir / "context.md").write_text(
            f"# Branch: {name}\n"
            f"**Exploration**: {explore_id}\n"
            f"**Question**: {question}\n"
            f"**Plan**: {approach['plan']}\n"
            f"**Status**: active\n"
            f"**Worktree**: {worktree_path}\n"
        )
        results.append({"name": name, "worktree": str(worktree_path)})

    # Update roadmap active branches
    main_md = agent_dir / "gcc" / "main.md"
    if main_md.exists():
        content = main_md.read_text()
        content = append_to_section(
            content, "## Active Branches", f"- **{explore_id}**: {question}"
        )
        main_md.write_text(content)

    return (
        f"Exploration {explore_id} created.\n"
        + "\n".join(f"- {r['name']}: {r['worktree']}" for r in results)
    )


@tool
def gcc_try_approach(explore_id: str, approach_name: str, actions: str) -> str:
    """Log what you implemented in a worktree.

    Args:
        explore_id: The exploration ID
        approach_name: Name of the approach
        actions: Description of what was implemented
    """
    agent_dir = get_agent_dir()
    branch_dir = agent_dir / "gcc" / "branches" / f"{explore_id}-{approach_name}"
    commits_dir = branch_dir / "commits"
    num = len(list(commits_dir.glob("*.md"))) + 1

    (commits_dir / f"{num:03d}.md").write_text(
        f"# {approach_name}: Attempt {num}\n"
        f"**Date**: {datetime.now().isoformat()}\n\n"
        f"## Actions\n{actions}\n"
    )

    worktree = agent_dir / "worktrees" / explore_id / approach_name
    subprocess.run(["git", "-C", str(worktree), "add", "-A"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(worktree),
            "commit",
            "-m",
            f"gcc: {explore_id}/{approach_name} attempt {num}",
        ],
        capture_output=True,
    )
    return f"Recorded attempt {num} for {approach_name}."


@tool
def gcc_evaluate(
    explore_id: str, evaluation: str, winner: str, reasoning: str
) -> str:
    """Compare approaches and pick a winner.

    Args:
        explore_id: The exploration ID
        evaluation: Detailed comparison of approaches
        winner: Name of the winning approach
        reasoning: Why this approach won
    """
    agent_dir = get_agent_dir()
    branches_dir = agent_dir / "gcc" / "branches"
    approaches = [
        d.name.replace(f"{explore_id}-", "")
        for d in branches_dir.iterdir()
        if d.name.startswith(explore_id)
    ]

    for approach in approaches:
        ctx = branches_dir / f"{explore_id}-{approach}" / "context.md"
        content = ctx.read_text()
        status = "winner" if approach == winner else "rejected"
        content = content.replace("**Status**: active", f"**Status**: {status}")
        content += f"\n## Evaluation\n{evaluation}\n**Reasoning**: {reasoning}\n"
        ctx.write_text(content)

    # Record as GCC commit
    commits_dir = agent_dir / "gcc" / "commits"
    commits_dir.mkdir(parents=True, exist_ok=True)
    num = len(list(commits_dir.glob("*.md"))) + 1

    approach_details = []
    for a in approaches:
        for cf in sorted(
            (branches_dir / f"{explore_id}-{a}" / "commits").glob("*.md")
        ):
            approach_details.append(f"### {a}\n{cf.read_text()}")

    (commits_dir / f"{num:03d}.md").write_text(
        f"# Commit {num:03d}: Exploration resolved — {explore_id}\n"
        f"**Date**: {datetime.now().isoformat()}\n"
        f"**Type**: exploration\n\n"
        f"## Approaches\n"
        + "\n".join(
            f"- **{a}**" + (" (winner)" if a == winner else " (rejected)")
            for a in approaches
        )
        + f"\n\n## Evaluation\n{evaluation}\n\n"
        f"## Decision\nWinner: **{winner}** — {reasoning}\n\n"
        f"## Details\n" + "\n".join(approach_details)
    )

    return f"Winner: {winner}. Call gcc_adopt to apply."


@tool
def gcc_adopt(explore_id: str, winner: str) -> str:
    """Merge the winning approach and clean up worktrees.

    Args:
        explore_id: The exploration ID
        winner: Name of the winning approach to merge
    """
    agent_dir = get_agent_dir()
    winner_branch = f"gcc/{explore_id}/{winner}"

    subprocess.run(
        [
            "git",
            "merge",
            winner_branch,
            "--no-edit",
            "-m",
            f"gcc: adopt {explore_id}/{winner}",
        ],
        check=True,
    )

    # Clean up worktrees
    worktrees_dir = agent_dir / "worktrees" / explore_id
    if worktrees_dir.exists():
        for d in worktrees_dir.iterdir():
            subprocess.run(
                ["git", "worktree", "remove", str(d), "--force"],
                capture_output=True,
            )
        worktrees_dir.rmdir()

    # Clean up branches
    branches_dir = agent_dir / "gcc" / "branches"
    for d in branches_dir.iterdir():
        if d.name.startswith(explore_id):
            branch_name = (
                f"gcc/{explore_id}/{d.name.replace(f'{explore_id}-', '')}"
            )
            subprocess.run(
                ["git", "branch", "-D", branch_name], capture_output=True
            )

    remove_active_branch(explore_id)
    return f"Adopted {winner}. Worktrees cleaned up."
