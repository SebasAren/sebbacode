
draft_roadmap extracts user_request + memory L0/L1/L2 + roadmap/briefing/target_files from state, uses planning prompt with LLM to generate initial roadmap draft stored in state (not on disk)
GCC commit files (`.agent/gcc/*.md`) are produced by `finalize_todo` in `src/sebba_code/nodes/extract.py`, not by a dedicated memory extraction step. This function handles finalizing todo items and persisting them to the gcc directory as part of the planning output pipeline.
## GCC Commit File Production

GCC commit files (`.agent/gcc/*.md`) use a timestamp-based naming/format produced by `finalize_todo` in `src/sebba_code/nodes/extract.py`. The `commit_changes` node must read from these same file patterns to integrate with the existing workflow — not from a separate memory extraction step.