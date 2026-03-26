# Memory Extraction Location

## Key Finding
Memory extraction (L1/L2 writes) is **not** centralized in `src/sebba_code/memory/`.

## Actual Location
Memory writes are **distributed across node implementations** in `src/sebba_code/nodes/`:
- `context.py`
- `rules.py`
- `deepening.py`

The `src/sebba_code/memory/` directory appears to be empty, deprecated, or renamed.

## Implication
When investigating memory behavior or adding memory features, examine node implementations rather than looking for a dedicated memory extraction layer.