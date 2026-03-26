"""Memory package — dual-tier L1/L2 storage with cheap-LLM summarisation.

Public API
----------
:py:mod:`layers <sebba_code.memory.layers>`
    ``MemoryLayer`` — reads and writes L1 (summary) and L2 (detailed) files.

:py:mod:`summarize <sebba_code.memory.summarize>`
    ``summarise_l2_to_l1`` — condense a single L2 entry using the cheap LLM.
    ``summarise_topic_to_l1`` — consolidate all L2 entries for a topic into one L1.

:py:mod:`hook <sebba_code.memory.hook>`
    ``post_extraction_hook`` — call this after extraction writes L2 to trigger
    async L1 summarisation.
    ``summarise_and_write`` — synchronous one-shot L2→L1 pipeline.
"""

from sebba_code.memory.hook import (
    close_executor,
    post_extraction_hook,
    reset_executor,
    summarise_and_write,
)
from sebba_code.memory.layers import (
    L1Summary,
    L2Entry,
    MemoryLayer,
    MemoryLayerConfig,
    content_hash,
    topic_from_path,
)
from sebba_code.memory.summarize import (
    summarise_l2_to_l1,
    summarise_topic_to_l1,
)

__all__ = [
    # layers
    "L1Summary",
    "L2Entry",
    "MemoryLayer",
    "MemoryLayerConfig",
    "content_hash",
    "topic_from_path",
    # summarize
    "summarise_l2_to_l1",
    "summarise_topic_to_l1",
    # hook
    "post_extraction_hook",
    "summarise_and_write",
    "reset_executor",
    "close_executor",
]
