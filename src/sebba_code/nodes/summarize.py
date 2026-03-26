"""L2→L1 summarization node — downstream of extract_session."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

from sebba_code.memory.hook import post_extraction_hook
from sebba_code.state import AgentState

logger = logging.getLogger("sebba_code")

_SUMMARIZE_OVERALL_TIMEOUT = 90  # seconds


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
        # Run in a guarded thread so we can enforce an overall timeout
        # and never block the graph indefinitely.
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                post_extraction_hook,
                l2_entries=l2_entries,
                topic="session",
                background=False,
                consolidate=False,
            )
            summaries = future.result(timeout=_SUMMARIZE_OVERALL_TIMEOUT)

        # If background=False, returns the list directly
        if not isinstance(summaries, list):
            summaries = []
        logger.info(
            "summarize_to_l1: wrote %d L1 summary(ies)",
            len(summaries),
        )

        return {
            "l1_summaries": [s.to_dict() for s in summaries],
        }

    except FuturesTimeout:
        logger.warning(
            "summarize_to_l1: overall timeout (%ds) exceeded — continuing to END",
            _SUMMARIZE_OVERALL_TIMEOUT,
        )
        return {}
    except Exception as exc:
        # Never let summarisation failure crash the graph.
        logger.warning(
            "summarize_to_l1: hook raised %s — continuing to END",
            exc,
            exc_info=True,
        )
        return {}
