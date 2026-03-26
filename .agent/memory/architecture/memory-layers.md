# Dual-Tier Memory Layer Architecture

## Overview
MemoryLayer provides a dual-tier storage system with L2 (deep-dive, topic-specific) and L1 (summary/condensed) operations.

## Core Operations
- `read_l2(key)`: Retrieve full L2 content
- `write_l1(key, content)`: Store condensed L1 summary
- `write_l2(key, content)`: Store full L2 content

## L2→L1 Summarization Flow
1. Extraction writes to L2
2. Post-extraction hook triggers summarization
3. Content-length gating (50 char threshold) determines if summarization needed
4. Cheap LLM model condenses L2 → L1
5. L1 stored alongside or replacing L2 reference

## Implementation Pattern
```python
# Separate module for isolation (seabba_code/memory/summarize.py)
# Use dataclasses for L1Summary, L2Summary type safety
# Hook into extract.py post-extraction pipeline
```

## Key Decisions
- Content-length threshold gates summarization (avoids trivial content)
- Separate summarize.py keeps logic isolated from storage layer
- Dataclasses provide type safety for summary models