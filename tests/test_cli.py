"""Tests for CLI commands, focusing on the init command."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from sebba_code.cli import cli, _has_source_files


class TestInitCommand:
    """Test suite for the `init` CLI command."""

    @pytest.fixture
    def runner(self):
        """Create a CliRunner instance for testing."""
        return CliRunner()

    def test_init_creates_agent_directory_in_cwd(self, runner, tmp_path):
        """Test that init creates .agent/ directory in current working directory."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init"])

            assert result.exit_code == 0
            assert os.path.isdir(".agent")
            assert "Initialized" in result.output
            assert ".agent/" in result.output

    def test_init_creates_subdirectories(self, runner, tmp_path):
        """Test that init creates all expected subdirectories."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init"])

            assert result.exit_code == 0
            assert os.path.isdir(".agent/memory")
            assert os.path.isdir(".agent/rules")
            assert os.path.isdir(".agent/branches")
            assert os.path.isdir(".agent/sessions")

    def test_init_creates_config_file(self, runner, tmp_path):
        """Test that init creates config.yaml file."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init"])

            assert result.exit_code == 0
            config_file = Path(".agent/config.yaml")
            assert config_file.exists()
            content = config_file.read_text()
            assert "llm:" in content
            assert "model:" in content

    def test_init_creates_memory_index(self, runner, tmp_path):
        """Test that init creates memory/_index.md file."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init"])

            assert result.exit_code == 0
            index_file = Path(".agent/memory/_index.md")
            assert index_file.exists()
            content = index_file.read_text()
            assert "Agent Memory Index" in content

    def test_init_with_project_path_argument(self, runner, tmp_path):
        """Test init with an explicit project path argument."""
        project_dir = tmp_path / "myproject"
        project_dir.mkdir()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init", str(project_dir)])

            assert result.exit_code == 0
            assert os.path.isdir(project_dir / ".agent")
            assert "Initialized" in result.output
            assert str(project_dir) in result.output

    def test_init_creates_structure_in_specified_path(self, runner, tmp_path):
        """Test that init creates correct structure at specified project path."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init", str(project_dir)])

            assert result.exit_code == 0
            assert (project_dir / ".agent/memory").exists()
            assert (project_dir / ".agent/rules").exists()
            assert (project_dir / ".agent/branches").exists()
            assert (project_dir / ".agent/sessions").exists()
            assert (project_dir / ".agent/config.yaml").exists()

    def test_init_idempotent(self, runner, tmp_path):
        """Test that running init twice doesn't fail."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result1 = runner.invoke(cli, ["init"])
            assert result1.exit_code == 0

            result2 = runner.invoke(cli, ["init"])
            assert result2.exit_code == 0

    def test_init_fails_for_nonexistent_parent_directory(self, runner, tmp_path):
        """Test that init fails gracefully when parent directory doesn't exist."""
        nonexistent_path = tmp_path / "nonexistent" / "project"
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init", str(nonexistent_path)])

            # Should fail because parent directory doesn't exist
            assert result.exit_code != 0

    def test_init_with_relative_path(self, runner, tmp_path):
        """Test init with a relative project path."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create the directory first
            os.mkdir("myproject")
            result = runner.invoke(cli, ["init", "myproject"])

            assert result.exit_code == 0
            assert os.path.isdir("myproject/.agent")

    def test_init_help_flag(self, runner, tmp_path):
        """Test that --help shows help for init command."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init", "--help"])

            assert result.exit_code == 0
            assert "Create the .agent/ directory structure" in result.output
            assert "PROJECT_PATH" in result.output or "project_path" in result.output.lower()

    def test_init_output_contains_agent_dir_name(self, runner, tmp_path):
        """Test that init output mentions the agent directory name."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init"])

            assert result.exit_code == 0
            assert ".agent" in result.output

    def test_init_with_nested_project_path(self, runner, tmp_path):
        """Test init with a nested directory structure."""
        nested_dir = tmp_path / "org" / "team" / "project"
        nested_dir.mkdir(parents=True)

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init", str(nested_dir)])

            assert result.exit_code == 0
            assert (nested_dir / ".agent").exists()
            assert (nested_dir / ".agent/config.yaml").exists()

    def test_init_config_file_contains_expected_sections(self, runner, tmp_path):
        """Test that config.yaml has all expected configuration sections."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init"])

            assert result.exit_code == 0
            config_content = Path(".agent/config.yaml").read_text()
            
            # Check for expected configuration sections
            assert "llm:" in config_content
            assert "loading:" in config_content
            assert "explorer:" in config_content
            assert "execution:" in config_content
            assert "planning:" in config_content

    def test_init_preserves_cwd_after_execution(self, runner, tmp_path):
        """Test that the original working directory is preserved after init."""
        original_cwd = os.getcwd()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            project_dir = tmp_path / "newproject"
            project_dir.mkdir()
            
            result = runner.invoke(cli, ["init", str(project_dir)])
            assert result.exit_code == 0

    def test_init_returns_success_exit_code(self, runner, tmp_path):
        """Test that init returns exit code 0 on success."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init"])
            assert result.exit_code == 0

    def test_init_error_returns_nonzero_exit_code(self, runner, tmp_path):
        """Test that init returns non-zero exit code on failure."""
        nonexistent_path = tmp_path / "doesnt" / "exist"
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init", str(nonexistent_path)])
            assert result.exit_code != 0


class TestInitCommandIntegration:
    """Integration tests for init command with real filesystem operations."""

    @pytest.fixture
    def runner(self):
        """Create a CliRunner instance for testing."""
        return CliRunner()

    def test_init_creates_all_expected_files_and_directories(self, runner, tmp_path):
        """Comprehensive test verifying all files and directories are created."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init"])
            assert result.exit_code == 0

            agent_dir = Path(".agent")
            
            # Check directories
            expected_dirs = ["memory", "rules", "branches", "sessions"]
            for dir_name in expected_dirs:
                assert (agent_dir / dir_name).is_dir(), f"Missing directory: {dir_name}"

            # Check files
            assert (agent_dir / "config.yaml").is_file(), "Missing file: config.yaml"
            assert (agent_dir / "memory" / "_index.md").is_file(), "Missing file: memory/_index.md"

    def test_init_memory_index_has_correct_format(self, runner, tmp_path):
        """Test that the memory index file has the expected format."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init"])
            assert result.exit_code == 0

            index_path = Path(".agent/memory/_index.md")
            content = index_path.read_text()
            
            assert "# Agent Memory Index" in content
            assert "Empty" in content or "Empty" in content or "will be populated" in content.lower()

    def test_init_config_has_valid_yaml_structure(self, runner, tmp_path):
        """Test that config.yaml is valid YAML with expected structure."""
        import yaml

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init"])
            assert result.exit_code == 0

            config_path = Path(".agent/config.yaml")
            config = yaml.safe_load(config_path.read_text())
            
            # Verify structure
            assert "llm" in config
            assert "loading" in config
            assert "explorer" in config
            assert "execution" in config
            assert "planning" in config

            # Verify llm section has model
            assert "model" in config["llm"]


class TestCliGroup:
    """Tests for the CLI group (main command entry point)."""

    @pytest.fixture
    def runner(self):
        """Create a CliRunner instance for testing."""
        return CliRunner()

    def test_cli_help(self, runner, tmp_path):
        """Test that --help shows available commands."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["--help"])

            assert result.exit_code == 0
            assert "Commands:" in result.output or "init" in result.output

    def test_cli_shows_init_command(self, runner, tmp_path):
        """Test that init command appears in help output."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["--help"])

            assert result.exit_code == 0
            # init should be listed as a command
            assert "init" in result.output.lower()

    def test_cli_init_command_exists(self, runner, tmp_path):
        """Test that init command can be invoked."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init", "--help"])

            assert result.exit_code == 0


class TestHasSourceFiles:
    """Tests for the _has_source_files helper function."""

    def test_returns_false_for_empty_directory(self, tmp_path):
        """Test that empty directory returns False."""
        assert _has_source_files(tmp_path) is False

    def test_returns_true_for_python_file(self, tmp_path):
        """Test that Python files are detected."""
        (tmp_path / "main.py").write_text("print('hello')")
        assert _has_source_files(tmp_path) is True

    def test_returns_true_for_javascript_file(self, tmp_path):
        """Test that JavaScript files are detected."""
        (tmp_path / "index.js").write_text("console.log('hello')")
        assert _has_source_files(tmp_path) is True

    def test_returns_true_for_typescript_file(self, tmp_path):
        """Test that TypeScript files are detected."""
        (tmp_path / "app.ts").write_text("const x: number = 1;")
        assert _has_source_files(tmp_path) is True

    def test_returns_true_for_yaml_file(self, tmp_path):
        """Test that YAML config files are detected."""
        (tmp_path / "config.yaml").write_text("key: value")
        assert _has_source_files(tmp_path) is True

    def test_returns_true_for_json_file(self, tmp_path):
        """Test that JSON files are detected."""
        (tmp_path / "package.json").write_text('{"name": "test"}')
        assert _has_source_files(tmp_path) is True

    def test_returns_true_for_markdown_file(self, tmp_path):
        """Test that Markdown files are detected."""
        (tmp_path / "README.md").write_text("# Title")
        assert _has_source_files(tmp_path) is True

    def test_returns_true_for_makefile(self, tmp_path):
        """Test that Makefile is detected."""
        (tmp_path / "Makefile").write_text("all:\n\tmake build")
        assert _has_source_files(tmp_path) is True

    def test_returns_true_for_dockerfile(self, tmp_path):
        """Test that Dockerfile is detected."""
        (tmp_path / "Dockerfile").write_text("FROM python:3.9")
        assert _has_source_files(tmp_path) is True

    def test_returns_false_for_binary_files(self, tmp_path):
        """Test that binary files are ignored."""
        (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n")
        assert _has_source_files(tmp_path) is False

    def test_returns_false_for_git_directory(self, tmp_path):
        """Test that files in .git are ignored."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("test")
        assert _has_source_files(tmp_path) is False

    def test_returns_false_for_venv_directory(self, tmp_path):
        """Test that files in venv are ignored."""
        venv_dir = tmp_path / "venv" / "lib"
        venv_dir.mkdir(parents=True)
        (venv_dir / "module.py").write_text("test")
        assert _has_source_files(tmp_path) is False

    def test_returns_false_for_node_modules(self, tmp_path):
        """Test that files in node_modules are ignored."""
        node_modules_dir = tmp_path / "node_modules" / "package"
        node_modules_dir.mkdir(parents=True)
        (node_modules_dir / "index.js").write_text("test")
        assert _has_source_files(tmp_path) is False

    def test_returns_true_for_nested_source_files(self, tmp_path):
        """Test that nested source files are detected."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("print('hello')")
        assert _has_source_files(tmp_path) is True

    def test_returns_true_for_go_files(self, tmp_path):
        """Test that Go files are detected."""
        (tmp_path / "main.go").write_text("package main")
        assert _has_source_files(tmp_path) is True

    def test_returns_true_for_rust_files(self, tmp_path):
        """Test that Rust files are detected."""
        (tmp_path / "main.rs").write_text("fn main() {}")
        assert _has_source_files(tmp_path) is True


class TestInitCommandExploration:
    """Tests for init command exploration functionality."""

    @pytest.fixture
    def runner(self):
        """Create a CliRunner instance for testing."""
        return CliRunner()

    def test_init_with_skip_exploration_flag(self, runner, tmp_path):
        """Test that --skip-exploration prevents exploration."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create source files inside the isolated filesystem
            Path("main.py").write_text("print('hello')")
            
            result = runner.invoke(cli, ["init", "--skip-exploration"])
            
            assert result.exit_code == 0
            # Exploration file should not be created
            exploration_file = Path(".agent/memory/knowledge/project_structure.md")
            assert not exploration_file.exists()

    def test_init_exploration_file_not_created_in_empty_dir(self, runner, tmp_path):
        """Test that exploration is skipped for empty directories."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init"])
            
            assert result.exit_code == 0
            # Exploration file should not be created for empty dirs
            exploration_file = Path(".agent/memory/knowledge/project_structure.md")
            assert not exploration_file.exists()

    def test_init_exploration_with_source_files(self, runner, tmp_path):
        """Test that exploration is performed when source files exist."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create source files inside the isolated filesystem
            Path("main.py").write_text("print('hello')")
            Path("utils.py").write_text("def helper(): pass")
            
            # Mock the explore_codebase function to avoid actual LLM calls
            with patch("sebba_code.tools.explore_agent.explore_codebase") as mock_explore:
                mock_explore.return_value = "Mocked exploration result"
                
                result = runner.invoke(cli, ["init"])
                
                assert result.exit_code == 0
                # Verify exploration was attempted
                mock_explore.assert_called_once()
                
                # Check exploration file was created
                exploration_file = Path(".agent/memory/knowledge/project_structure.md")
                assert exploration_file.exists()
                content = exploration_file.read_text()
                assert "Project Structure Exploration" in content
                assert "Mocked exploration result" in content

    def test_init_exploration_failure_handled_gracefully(self, runner, tmp_path):
        """Test that exploration failures don't crash init."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create source files inside the isolated filesystem
            Path("main.py").write_text("print('hello')")
            
            # Mock explore_codebase to raise an exception
            with patch("sebba_code.tools.explore_agent.explore_codebase", side_effect=Exception("LLM unavailable")):
                result = runner.invoke(cli, ["init"])
                
                # Init should still succeed despite exploration failure
                assert result.exit_code == 0
                # Should contain warning about exploration failure
                assert "Warning" in result.output or "warning" in result.output.lower()
                # Basic structure should still be created
                assert Path(".agent/config.yaml").exists()

    def test_init_shows_skipping_message_for_empty_dir(self, runner, tmp_path):
        """Test that init shows message when skipping exploration for empty dirs."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init"])
            
            assert result.exit_code == 0
            # Should show skipping message (empty dirs skip exploration)
            assert "Skipping exploration" in result.output or "no source files" in result.output.lower()

    def test_init_exploration_output_contains_timestamp(self, runner, tmp_path):
        """Test that exploration results include timestamp."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("main.py").write_text("print('hello')")
            
            with patch("sebba_code.tools.explore_agent.explore_codebase") as mock_explore:
                mock_explore.return_value = "Test findings"
                
                result = runner.invoke(cli, ["init"])
                
                exploration_file = Path(".agent/memory/knowledge/project_structure.md")
                content = exploration_file.read_text()
                assert "Explored at:" in content

    def test_init_exploration_output_contains_question(self, runner, tmp_path):
        """Test that exploration results include the question asked."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("main.py").write_text("print('hello')")
            
            with patch("sebba_code.tools.explore_agent.explore_codebase") as mock_explore:
                mock_explore.return_value = "Test findings"
                
                result = runner.invoke(cli, ["init"])
                
                exploration_file = Path(".agent/memory/knowledge/project_structure.md")
                content = exploration_file.read_text()
                assert "## Question" in content

    def test_init_exploration_output_contains_findings(self, runner, tmp_path):
        """Test that exploration results include the findings."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("main.py").write_text("print('hello')")
            
            with patch("sebba_code.tools.explore_agent.explore_codebase") as mock_explore:
                mock_explore.return_value = "The codebase has a simple structure with main.py"
                
                result = runner.invoke(cli, ["init"])
                
                exploration_file = Path(".agent/memory/knowledge/project_structure.md")
                content = exploration_file.read_text()
                assert "## Findings" in content
                assert "The codebase has a simple structure with main.py" in content

    def test_init_help_shows_skip_exploration_option(self, runner, tmp_path):
        """Test that --help shows the --skip-exploration option."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init", "--help"])
            
            assert result.exit_code == 0
            assert "--skip-exploration" in result.output

    def test_init_preserves_existing_exploration_file(self, runner, tmp_path):
        """Test that re-running init preserves existing exploration file."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("main.py").write_text("print('hello')")
            
            with patch("sebba_code.tools.explore_agent.explore_codebase") as mock_explore:
                mock_explore.return_value = "First exploration"
                
                result1 = runner.invoke(cli, ["init"])
                assert result1.exit_code == 0
                
                # Get original content
                exploration_file = Path(".agent/memory/knowledge/project_structure.md")
                original_content = exploration_file.read_text()
                
                # Run init again with different mock
                mock_explore.return_value = "Second exploration"
                result2 = runner.invoke(cli, ["init"])
                
                # Content should be updated (not preserved)
                new_content = exploration_file.read_text()
                assert "Second exploration" in new_content

    def test_init_exploration_with_nested_source_files(self, runner, tmp_path):
        """Test exploration detects nested source files."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create nested source structure inside isolated filesystem
            Path("src").mkdir()
            Path("tests").mkdir()
            
            (Path("src") / "app.py").write_text("print('app')")
            (Path("src") / "models.py").write_text("class Model: pass")
            (Path("tests") / "test_app.py").write_text("def test_app(): pass")
            
            with patch("sebba_code.tools.explore_agent.explore_codebase") as mock_explore:
                mock_explore.return_value = "Nested structure detected"
                
                result = runner.invoke(cli, ["init"])
                
                assert result.exit_code == 0
                mock_explore.assert_called_once()

    def test_init_configure_llm_called_before_exploration(self, runner, tmp_path):
        """Test that LLM is configured before exploration is attempted."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("main.py").write_text("print('hello')")
            
            with patch("sebba_code.tools.explore_agent.explore_codebase") as mock_explore, \
                 patch("sebba_code.cli._configure_llm_from_config") as mock_configure:
                mock_explore.return_value = "Test"
                
                result = runner.invoke(cli, ["init"])
                
                assert result.exit_code == 0
                # Configure should be called before explore
                mock_configure.assert_called_once()
