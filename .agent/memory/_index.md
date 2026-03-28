# Agent Memory Index

- **architecture**: LangGraph StateGraph (12+ nodes); src-layout Python 3.11+; worker subgraph: recon→rules→deepen→llm_call→summarize→extract; CLI args→initial_state→graph state (single TypedDict); config precedence: CLI→file→defaults
- **planning**: Draft→critique→refine loop (max 3 iter); explore_codebase called BEFORE subagent delegation; EXPLORE_PATTERNS flags bypass; roadmap in state until planning_complete then written to .agent/roadmap.md; completed roadmaps archived to roadmaps/archive/
- **memory-pipeline**: L2 writes from extraction.py only; L1 via async post_extraction_hook condensation; 50-char min gate; content_hash for dedup; _index.md for L0 updates; max 20 L2 entries per topic with eviction
- **testing**: tmp_agent_dir + _make_state fixtures; hybrid git testing (mocked subprocess + real Git); mock invoke_with_timeout returns ≥10 words/40 chars; patch at usage site not definition; pytest from repo root; config via env var manipulation
- **tool-patterns**: code.py subprocess pattern for shell cmds; register in get_all_tools()+get_worker_tools(); workers get restricted set (no explore/try_approach/evaluate/adopt); recursion limit: 100 + (max_iterations × 10)
