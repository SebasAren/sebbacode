from pathlib import Path

import pytest

import sebba_code.constants


@pytest.fixture
def tmp_agent_dir(tmp_path: Path) -> Path:
    """Create a temporary .agent/ directory structure for testing."""
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir()

    # Memory
    memory_dir = agent_dir / "memory"
    memory_dir.mkdir()
    (memory_dir / "_index.md").write_text(
        "# Agent Memory Index\n\n"
        "- **architecture**: Monorepo, 2 apps (api, frontend)\n"
        "- **conventions**: TypeScript, vitest\n"
    )
    (memory_dir / "architecture.md").write_text(
        "# Architecture\n\nMonorepo with api and frontend apps.\n"
    )
    (memory_dir / "conventions.md").write_text(
        "# Conventions\n\nUse TypeScript strict mode.\n"
    )
    decisions_dir = memory_dir / "decisions"
    decisions_dir.mkdir()
    (decisions_dir / "_index.md").write_text("# Decision Log\nNo decisions recorded yet.\n")

    # Rules
    rules_dir = agent_dir / "rules"
    rules_dir.mkdir()
    (rules_dir / "global.md").write_text("# Global Rules\n\n- Always use strict TypeScript\n")
    (rules_dir / "testing.md").write_text(
        '---\npaths:\n  - "**/*.test.ts"\n  - "**/*.spec.ts"\n---\n'
        "# Testing Rules\n\n- Use vitest\n"
    )

    # Roadmap
    (agent_dir / "roadmap.md").write_text(
        "# Test Roadmap\n\n"
        "## Goal\nTest the agent.\n\n"
        "## Todos\n"
        "- [ ] First task\n"
        "- [ ] Second task\n\n"
        "## Target Files\n"
        "- src/app.ts\n"
        "- src/utils.ts\n\n"
        "## Decisions Made\nNone.\n\n"
        "## Constraints\n- Must work\n"
    )

    # Branches (for exploration)
    (agent_dir / "branches").mkdir()

    # Roadmap archive
    (agent_dir / "roadmaps" / "archive").mkdir(parents=True)

    # Sessions
    (agent_dir / "sessions").mkdir()

    # Override the global AGENT_DIR
    sebba_code.constants.init_agent_dir(agent_dir)

    yield agent_dir

    # Reset
    sebba_code.constants.init_agent_dir(Path(".agent"))
