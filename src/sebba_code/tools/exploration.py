"""Implements exploration tools using git worktrees for parallel approach evaluation."""

import subprocess
from datetime import datetime

from langchain_core.tools import tool

from sebba_code.constants import get_agent_dir


@tool
def explore(question: str, approaches: list[dict]) -> str:
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
        branch_name = f"explore/{explore_id}/{name}"
        worktree_path = worktrees_dir / explore_id / name

        subprocess.run(["git", "branch", branch_name], check=True)
        subprocess.run(
            ["git", "worktree", "add", str(worktree_path), branch_name],
            check=True,
        )

        branch_dir = agent_dir / "branches" / f"{explore_id}-{name}"
        branch_dir.mkdir(parents=True, exist_ok=True)
        (branch_dir / "context.md").write_text(
            f"# Branch: {name}\n"
            f"**Exploration**: {explore_id}\n"
            f"**Question**: {question}\n"
            f"**Plan**: {approach['plan']}\n"
            f"**Status**: active\n"
            f"**Worktree**: {worktree_path}\n"
        )
        results.append({"name": name, "worktree": str(worktree_path)})

    return (
        f"Exploration {explore_id} created.\n"
        + "\n".join(f"- {r['name']}: {r['worktree']}" for r in results)
    )


@tool
def try_approach(explore_id: str, approach_name: str, actions: str) -> str:
    """Log what you implemented in a worktree.

    Args:
        explore_id: The exploration ID
        approach_name: Name of the approach
        actions: Description of what was implemented
    """
    agent_dir = get_agent_dir()
    branch_dir = agent_dir / "branches" / f"{explore_id}-{approach_name}"

    # Append actions to context file
    ctx = branch_dir / "context.md"
    if ctx.exists():
        content = ctx.read_text()
        content += f"\n## Attempt\n{actions}\n"
        ctx.write_text(content)

    worktree = agent_dir / "worktrees" / explore_id / approach_name
    subprocess.run(["git", "-C", str(worktree), "add", "-A"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(worktree),
            "commit",
            "-m",
            f"explore: {explore_id}/{approach_name}",
        ],
        capture_output=True,
    )
    return f"Recorded attempt for {approach_name}."


@tool
def evaluate(
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
    branches_dir = agent_dir / "branches"
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

    return f"Winner: {winner}. Call adopt to apply."


@tool
def adopt(explore_id: str, winner: str) -> str:
    """Merge the winning approach and clean up worktrees.

    Args:
        explore_id: The exploration ID
        winner: Name of the winning approach to merge
    """
    agent_dir = get_agent_dir()
    winner_branch = f"explore/{explore_id}/{winner}"

    subprocess.run(
        [
            "git",
            "merge",
            winner_branch,
            "--no-edit",
            "-m",
            f"explore: adopt {explore_id}/{winner}",
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
    branches_dir = agent_dir / "branches"
    if branches_dir.exists():
        for d in branches_dir.iterdir():
            if d.name.startswith(explore_id):
                branch_name = (
                    f"explore/{explore_id}/{d.name.replace(f'{explore_id}-', '')}"
                )
                subprocess.run(
                    ["git", "branch", "-D", branch_name], capture_output=True
                )

    return f"Adopted {winner}. Worktrees cleaned up."
