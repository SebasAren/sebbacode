from sebba_code.tools.code import read_file, run_command, write_file
from sebba_code.tools.exploration import (
    gcc_adopt,
    gcc_evaluate,
    gcc_explore,
    gcc_try_approach,
)
from sebba_code.tools.memory import memory_query
from sebba_code.tools.progress import (
    add_todo,
    discover_files,
    gcc_commit,
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
        gcc_commit,
        mark_todo_done,
        add_todo,
        discover_files,
        # Exploration tools
        gcc_explore,
        gcc_try_approach,
        gcc_evaluate,
        gcc_adopt,
        # Memory tools
        memory_query,
    ]
