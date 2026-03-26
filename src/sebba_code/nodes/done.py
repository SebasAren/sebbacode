"""Implements the roadmap completion terminal node."""

import logging
import re
from datetime import date

from sebba_code.constants import get_agent_dir
from sebba_code.state import AgentState


logger = logging.getLogger("sebba_code")


def roadmap_done(state: AgentState) -> dict:
    """Handle roadmap completion — archive the finished roadmap."""
    logger.info("Roadmap completed")
    agent_dir = get_agent_dir()
    roadmap_path = agent_dir / "roadmap.md"

    if roadmap_path.exists():
        content = roadmap_path.read_text()

        # Generate a slug from the goal section
        slug = "roadmap"
        goal_match = re.search(r"## Goal\s*\n(.+)", content)
        if goal_match:
            slug = re.sub(r"[^a-z0-9]+", "-", goal_match.group(1).strip().lower())[:40]
            slug = slug.strip("-")

        archive_dir = agent_dir / "roadmaps" / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archive_dir / f"{date.today().isoformat()}-{slug}.md"

        # Handle name collision
        counter = 1
        while archive_path.exists():
            archive_path = archive_dir / f"{date.today().isoformat()}-{slug}-{counter}.md"
            counter += 1

        archive_path.write_text(content)
        roadmap_path.unlink()
        logger.info("Archived roadmap to %s", archive_path)

    return state
