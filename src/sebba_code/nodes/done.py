"""Implements the roadmap completion terminal node."""

import logging

from sebba_code.state import AgentState


logger = logging.getLogger("sebba_code")


def roadmap_done(state: AgentState) -> dict:
    """Handle roadmap completion."""
    logger.info("Roadmap completed")
    return state
