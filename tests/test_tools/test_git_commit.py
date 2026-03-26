"""Tests for git commit tool and git utility functions.

This module covers:
- git_run() helper function
- git_commit tool integration
- Real git operations with actual repositories
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic_core import ValidationError

from sebba_code.helpers.git import get_current_branch, git_run


class TestGitRun:
    """Test suite for the git_run() helper function."""

    @patch("subprocess.run")
    def test_runs_git_command(self, mock_run: MagicMock):
        """Verify git_run executes a git command with the given arguments."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="abc1234",
            stderr="",
        )

        result = git_run(["log", "-1", "--format=%H"])

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["git", "log", "-1", "--format=%H"]
        assert result.stdout == "abc1234"

    @patch("subprocess.run")
    def test_captures_output(self, mock_run: MagicMock):
        """Verify git_run captures stdout and stderr."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="feature-branch",
            stderr="",
        )

        result = git_run(["branch", "--show-current"])

        assert result.stdout.strip() == "feature-branch"

    @patch("subprocess.run")
    def test_returns_stderr(self, mock_run: MagicMock):
        """Verify git_run returns stderr in the result."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="fatal: not a git repository",
        )

        result = git_run(["status"])

        assert "not a git repository" in result.stderr

    @patch("subprocess.run")
    def test_respects_cwd_parameter(self, mock_run: MagicMock):
        """Verify git_run passes cwd to subprocess.run."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr="",
        )
        test_path = Path("/some/repo/path")

        git_run(["log"], cwd=test_path)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["cwd"] == test_path

    @patch("subprocess.run")
    def test_handles_complex_args(self, mock_run: MagicMock):
        """Verify git_run handles various git argument formats."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr="",
        )

        git_run([
            "log",
            "--oneline",
            "--all",
            "--graph",
            "--decorate",
            "-10",
        ])

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "git"
        assert "--oneline" in args
        assert "--all" in args


class TestGitRunIntegration:
    """Integration tests using real git commands."""

    def test_git_version_command(self, tmp_path: Path):
        """Verify git_run can execute a real git command."""
        result = git_run(["--version"], cwd=tmp_path)

        assert result.returncode == 0
        assert "git version" in result.stdout

    def test_git_run_in_new_repo(self, tmp_path: Path):
        """Verify git_run works in a freshly initialized repository."""
        # Initialize repo
        git_run(["init"], cwd=tmp_path)

        # Create and stage a file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, git!")

        # Commit
        git_run(["add", "test.txt"], cwd=tmp_path)
        result = git_run(
            ["commit", "-m", "Initial commit"],
            cwd=tmp_path,
        )

        assert result.returncode == 0
        assert "Initial commit" in result.stdout

    def test_git_log_returns_commit_hash(self, tmp_path: Path):
        """Verify git_run can retrieve commit information."""
        # Setup: create a commit
        git_run(["init"], cwd=tmp_path)
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        git_run(["add", "test.txt"], cwd=tmp_path)
        git_run(["commit", "-m", "test"], cwd=tmp_path)

        # Get the commit hash
        result = git_run(["rev-parse", "HEAD"], cwd=tmp_path)

        assert result.returncode == 0
        assert len(result.stdout.strip()) == 40  # Full SHA hash length


class TestGetCurrentBranch:
    """Test suite for the get_current_branch() function."""

    @patch("sebba_code.helpers.git.git_run")
    def test_returns_branch_name(self, mock_git_run: MagicMock):
        """Verify get_current_branch returns the current branch name."""
        mock_git_run.return_value = MagicMock(
            stdout="main\n",
            stderr="",
            returncode=0,
        )

        branch = get_current_branch()

        assert branch == "main"
        mock_git_run.assert_called_once_with(
            ["rev-parse", "--abbrev-ref", "HEAD"],
            cwd=None,
        )

    @patch("sebba_code.helpers.git.git_run")
    def test_strips_whitespace(self, mock_git_run: MagicMock):
        """Verify branch name is stripped of whitespace."""
        mock_git_run.return_value = MagicMock(
            stdout="  feature/my-branch  \n",
            stderr="",
            returncode=0,
        )

        branch = get_current_branch()

        assert branch == "feature/my-branch"

    @patch("sebba_code.helpers.git.git_run")
    def test_uses_provided_cwd(self, mock_git_run: MagicMock):
        """Verify get_current_branch respects the cwd parameter."""
        mock_git_run.return_value = MagicMock(
            stdout="develop\n",
            stderr="",
            returncode=0,
        )
        test_path = Path("/test/path")

        get_current_branch(cwd=test_path)

        mock_git_run.assert_called_once_with(
            ["rev-parse", "--abbrev-ref", "HEAD"],
            cwd=test_path,
        )


class TestGitCommitTool:
    """Test suite for the git_commit tool."""

    @patch("sebba_code.tools.git_commit.git_run")
    def test_commit_with_valid_message(self, mock_git_run: MagicMock):
        """Verify git_commit tool executes with a valid message."""
        from sebba_code.tools.git_commit import git_commit

        mock_git_run.return_value = MagicMock(
            returncode=0,
            stdout="[main abc1234] feat: add feature",
            stderr="",
        )

        result = git_commit.invoke({"message": "feat: add feature"})

        assert "Error" not in result
        mock_git_run.assert_called_once_with(
            ["commit", "-m", "feat: add feature"]
        )

    @patch("sebba_code.tools.git_commit.git_run")
    def test_commit_with_files_specified(self, mock_git_run: MagicMock):
        """Verify git_commit tool can commit specific files."""
        from sebba_code.tools.git_commit import git_commit

        mock_git_run.return_value = MagicMock(
            returncode=0,
            stdout="[main abc1234] update files",
            stderr="",
        )

        result = git_commit.invoke({
            "message": "update files",
            "files": ["src/app.py", "src/utils.py"],
        })

        mock_git_run.assert_called_once_with(
            ["commit", "-m", "update files", "--", "src/app.py", "src/utils.py"]
        )

    def test_commit_rejects_empty_message(self):
        """Verify git_commit tool rejects empty commit messages."""
        from sebba_code.tools.git_commit import git_commit

        result = git_commit.invoke({"message": ""})

        assert "Error" in result
        assert "empty" in result.lower()

    def test_commit_rejects_whitespace_only_message(self):
        """Verify git_commit tool rejects whitespace-only messages."""
        from sebba_code.tools.git_commit import git_commit

        result = git_commit.invoke({"message": "   \n\t  "})

        assert "Error" in result

    def test_commit_rejects_none_message(self):
        """Verify git_commit tool rejects None commit messages via validation."""
        from sebba_code.tools.git_commit import git_commit

        with pytest.raises(ValidationError, match="message"):
            git_commit.invoke({"message": None})

    @patch("sebba_code.tools.git_commit.git_run")
    def test_message_with_shell_metacharacters(self, mock_git_run: MagicMock):
        """Verify shell metacharacters in messages are not interpreted."""
        from sebba_code.tools.git_commit import git_commit

        mock_git_run.return_value = MagicMock(
            returncode=0,
            stdout="[main abc1234] committed",
            stderr="",
        )

        git_commit.invoke({"message": 'fix: handle "quotes" & $(subshell) `backticks`'})

        # The message must be passed as a single list element, not shell-expanded
        args = mock_git_run.call_args[0][0]
        assert args == [
            "commit", "-m", 'fix: handle "quotes" & $(subshell) `backticks`'
        ]

    @patch("sebba_code.tools.git_commit.git_run")
    def test_files_with_spaces_and_special_chars(self, mock_git_run: MagicMock):
        """Verify file paths with special characters are passed safely."""
        from sebba_code.tools.git_commit import git_commit

        mock_git_run.return_value = MagicMock(
            returncode=0,
            stdout="committed",
            stderr="",
        )

        git_commit.invoke({
            "message": "fix: update",
            "files": ["path with spaces/file.py", "file;rm -rf.txt"],
        })

        args = mock_git_run.call_args[0][0]
        assert args == [
            "commit", "-m", "fix: update",
            "--", "path with spaces/file.py", "file;rm -rf.txt",
        ]

    @patch("sebba_code.tools.git_commit.git_run")
    def test_commit_with_empty_files_list(self, mock_git_run: MagicMock):
        """Verify empty files list is treated same as None."""
        from sebba_code.tools.git_commit import git_commit

        mock_git_run.return_value = MagicMock(
            returncode=0,
            stdout="committed",
            stderr="",
        )

        git_commit.invoke({"message": "test", "files": []})

        mock_git_run.assert_called_once_with(["commit", "-m", "test"])

    @patch("sebba_code.tools.git_commit.git_run")
    def test_nonzero_exit_code_included(self, mock_git_run: MagicMock):
        """Verify non-zero exit codes are reported in output."""
        from sebba_code.tools.git_commit import git_commit

        mock_git_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="nothing to commit",
        )

        result = git_commit.invoke({"message": "test"})

        assert "Exit code: 1" in result
        assert "nothing to commit" in result


class TestGitCommitIntegration:
    """Integration tests for git commit operations with real git."""

    def test_commit_creates_valid_commit(self, tmp_path: Path):
        """Verify a real git commit creates a valid commit object."""
        # Initialize repository
        git_run(["init"], cwd=tmp_path)

        # Set git config to avoid author errors
        git_run(["config", "user.email", "test@example.com"], cwd=tmp_path)
        git_run(["config", "user.name", "Test User"], cwd=tmp_path)

        # Create a file and commit it
        test_file = tmp_path / "hello.txt"
        test_file.write_text("Hello, World!")

        git_run(["add", "hello.txt"], cwd=tmp_path)
        commit_result = git_run(
            ["commit", "-m", "feat: add hello world"],
            cwd=tmp_path,
        )

        assert commit_result.returncode == 0

        # Verify the commit exists
        log_result = git_run(["log", "--oneline"], cwd=tmp_path)
        assert "feat: add hello world" in log_result.stdout

    def test_commit_returns_hash_on_success(self, tmp_path: Path):
        """Verify successful commit returns a valid SHA hash."""
        git_run(["init"], cwd=tmp_path)
        git_run(["config", "user.email", "test@example.com"], cwd=tmp_path)
        git_run(["config", "user.name", "Test User"], cwd=tmp_path)

        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        git_run(["add", "test.txt"], cwd=tmp_path)
        git_run(["commit", "-m", "initial"], cwd=tmp_path)

        # Get the commit hash
        result = git_run(["rev-parse", "HEAD"], cwd=tmp_path)
        commit_hash = result.stdout.strip()

        assert len(commit_hash) == 40
        assert commit_hash.isalnum()

    def test_commit_no_staged_changes(self, tmp_path: Path):
        """Verify committing with no staged changes fails appropriately."""
        git_run(["init"], cwd=tmp_path)
        git_run(["config", "user.email", "test@example.com"], cwd=tmp_path)
        git_run(["config", "user.name", "Test User"], cwd=tmp_path)

        result = git_run(["commit", "-m", "empty commit"], cwd=tmp_path)

        assert result.returncode != 0
        assert "nothing to commit" in result.stderr or "nothing to commit" in result.stdout.lower()

    def test_commit_uses_correct_author(self, tmp_path: Path):
        """Verify commits use the configured author."""
        test_email = "author@test.com"
        test_name = "Test Author"

        git_run(["init"], cwd=tmp_path)
        git_run(["config", "user.email", test_email], cwd=tmp_path)
        git_run(["config", "user.name", test_name], cwd=tmp_path)

        test_file = tmp_path / "author_test.txt"
        test_file.write_text("testing author")
        git_run(["add", "author_test.txt"], cwd=tmp_path)
        git_run(["commit", "-m", "test author"], cwd=tmp_path)

        # Verify author in log
        result = git_run(
            ["log", "--format=%ae%n%an", "-1"],
            cwd=tmp_path,
        )

        assert test_email in result.stdout
        assert test_name in result.stdout

    def test_multiple_commits_history(self, tmp_path: Path):
        """Verify multiple commits create proper history."""
        git_run(["init"], cwd=tmp_path)
        git_run(["config", "user.email", "test@example.com"], cwd=tmp_path)
        git_run(["config", "user.name", "Test User"], cwd=tmp_path)

        # Make multiple commits
        for i in range(3):
            test_file = tmp_path / f"file{i}.txt"
            test_file.write_text(f"content {i}")
            git_run(["add", f"file{i}.txt"], cwd=tmp_path)
            git_run(["commit", "-m", f"chore: add file {i}"], cwd=tmp_path)

        # Verify all commits exist
        result = git_run(["log", "--oneline"], cwd=tmp_path)
        lines = [l for l in result.stdout.strip().split("\n") if l]

        assert len(lines) == 3
        assert all("chore: add file" in line for line in lines)
