# Agent Memory Index

(Empty — will be populated on first run)
CLI args → initial_state dict → graph state (not separate config)
TypedDict Optional[T] pattern: None = use default, avoids has_ flags
Constants: DEFAULT_MAX_TODOS = 5 in constants.py, referenced in nodes/extract.py
Conditional state population: only set Optional fields when explicitly provided
CLI args → initial_state dict → graph state (TypedDict, not separate config)
TypedDict Optional[T] pattern: None = use default; avoids has_* flags
Conditional state pop: only set Optional fields when explicitly provided
DEFAULT_MAX_TODOS = 5 in constants.py, referenced by nodes/extract.py
