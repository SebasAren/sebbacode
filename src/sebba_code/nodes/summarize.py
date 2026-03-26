"""L2→L1 summarization node — downstream of extract_session."""

from __future__ import annotations

import logging

from sebba_code.memory.hook import post_extraction_hook
from sebba_code.state import AgentState

logger = logging.getLogger("sebba_code")


def summarize_to_l1(state: AgentState) -> dict:
    """Condense L2 memory entries into L1 summaries.

    This node runs synchronously after ``extract_session`` to ensure L1
    summaries are written before the graph exits.  It reads L2 entries
    that were collected during extraction and triggers the summarisation
    pipeline.

    The hook is idempotent: re-running on the same L2 content increments
    version counters rather than creating duplicates.

    Args:
        state: Agent graph state containing ``l2_entries`` collected by
            ``extract_session``.

    Returns:
        A dict with ``l1_summaries`` key (list of L1Summary dicts) on
        success, or an empty dict if there is nothing to summarise.
        Failures are logged but never raise — the node always returns
        a valid dict so the graph can continue to END.
    """
    # Pull L2 entries that extract_session stashed in state
    l2_entries: list[dict] = state.get("l2_entries", [])

    if not l2_entries:
        logger.debug("summarize_to_l1: no L2 entries in state, skipping")
        return {}

    logger.info(
        "summarize_to_l1: processing %d L2 entries",
        len(l2_entries),
    )

    try:
        # Run synchronously (background=False) so L1 is fully written
        # before the graph reaches END.
        future_or_results = post_extraction_hook(
            l2_entries=l2_entries,
            topic="session",
            background=False,  # synchronous: wait for completion
            consolidate=False,  # one summary per L2 entry
        )

        # If background=False, returns the list directly
        summaries = future_or_results if isinstance(future_or_results, list) else []
        logger.info(
            "summarize_to_l1: wrote %d L1 summary(ies)",
            len(summaries),
        )

        return {
            "l1_summaries": [s.to_dict() for s in summaries],
        }

    except Exception as exc:
        # Never let summarisation failure crash the graph.
        logger.warning(
            "summarize_to_l1: hook raised %s — continuing to END",
            exc,
            exc_info=True,
        )
        return {}
