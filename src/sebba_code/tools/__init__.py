from sebba_code.tools.code import read_file, run_command, write_file
from sebba_code.tools.exploration import (
    adopt,
    evaluate,
    explore,
    try_approach,
)
from sebba_code.tools.memory import memory_query
from sebba_code.tools.progress import (
    add_todo,
    discover_files,
    mark_todo_done,
)


def get_all_tools() -> list:
    """Return all tools available to the executor."""
    return [
        # Code tools
        read_file,
        write_file,
        run_command,
        # Progress tools
        mark_todo_done,
        add_todo,
        discover_files,
        # Exploration tools
        explore,
        try_approach,
        evaluate,
        adopt,
        # Memory tools
        memory_query,
    ]
