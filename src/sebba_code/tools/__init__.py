from sebba_code.tools.code import read_file, run_command, write_file
from sebba_code.tools.explore_agent import explore_codebase
from sebba_code.tools.exploration import (
    adopt,
    evaluate,
    explore,
    try_approach,
)
from sebba_code.tools.git_commit import git_commit
from sebba_code.tools.memory import memory_query
from sebba_code.tools.progress import (
    add_subtask,
    mark_task_done,
    signal_blocked,
)
from sebba_code.tools.search import search_code, search_files


def get_all_tools() -> list:
    """Return all tools available to the executor (legacy, includes exploration)."""
    return [
        read_file,
        write_file,
        run_command,
        search_files,
        search_code,
        explore_codebase,
        mark_task_done,
        signal_blocked,
        add_subtask,
        explore,
        try_approach,
        evaluate,
        adopt,
        memory_query,
        git_commit,
    ]


def get_worker_tools() -> list:
    """Return tools available to a task worker."""
    return [
        read_file,
        write_file,
        run_command,
        search_files,
        search_code,
        explore_codebase,
        mark_task_done,
        signal_blocked,
        add_subtask,
        memory_query,
        git_commit,
    ]
