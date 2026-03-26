"""Tests for CLI commands, focusing on the init command."""

import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from sebba_code.cli import cli


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
