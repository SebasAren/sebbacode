# Execute Subgraph Architecture

## Overview
The execute subgraph handles todo execution with a 6-node worker pattern including timeout and error recovery.

## Components
- **Location**: `src/sebba_code/nodes/execute.py`
- **Worker implementation**: Contains the core execution loop
- **explore_bootstrap**: Entry point for subgraph initialization
- **Subgraph building patterns**: Used to construct the 6-node worker graph

## Key Patterns
- Worker system prompt building and message formatting functions
- Todo execution subgraph integrates with the main planning graph
- Timeout/error recovery built into worker node design

## Relationship to Planning
Post-execution flow: finalize_todo → TodoSummary in state → extract_session reads summaries → distills into lasting memory/rules

Archived roadmaps: .agent/roadmaps/archive/{date}-{slug}.md