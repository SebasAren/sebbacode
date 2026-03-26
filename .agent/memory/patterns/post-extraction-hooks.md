# Post-Extraction Hook Pattern

## Purpose
Trigger downstream processing after extraction completes.

## Pattern
Wire hooks into post-extraction pipeline in `src/sebba_code/nodes/extract.py`:
1. Extraction completes → writes to L2
2. Hook fires on extraction success
3. Hook performs side effects (summarization, indexing, etc.)

## Test Coverage
- Test sync and async flows
- Cover hook timing (after L2 write)
- Verify threshold logic and async compatibility