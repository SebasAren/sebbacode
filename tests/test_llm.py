"""Tests for the LLM client module, focusing on cheap model config integration."""

import os
import tempfile
import shutil
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch


# Ensure test environment doesn't have conflicting env vars set
def _clear_llm_env():
    """Clear all LLM-related environment variables for test isolation."""
    for key in [
        "SEBBA_MODEL", "SEBBA_MODEL_PROVIDER", "SEBBA_BASE_URL", "SEBBA_API_KEY",
        "SEBBA_CHEAP_MODEL", "SEBBA_CHEAP_MODEL_PROVIDER",
        "SEBBA_CHEAP_BASE_URL", "SEBBA_CHEAP_API_KEY",
    ]:
        os.environ.pop(key, None)


class TestGetCheapLlmConfig(TestCase):
    """Test that _get_cheap_llm_config reads from config, env, then defaults.

    Precedence order (highest to lowest):
    1. config.yaml values (highest priority)
    2. Environment variables
    3. Hardcoded defaults (lowest priority)
    """

    def setUp(self):
        _clear_llm_env()
        self.agent_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.agent_dir, ignore_errors=True)
        _clear_llm_env()
        from sebba_code import llm
        llm.reset_llm_clients()

    def test_cheap_config_from_yaml(self):
        """Verify cheap_model is read from config.yaml (yaml has highest priority)."""
        config_yaml = self.agent_dir / "config.yaml"
        config_yaml.write_text(
            "llm:\n"
            "  cheap_model: custom-cheap-model\n"
            "  cheap_model_provider: openai\n"
            "  cheap_base_url: https://api.example.com\n"
            "  cheap_api_key: sk-test123\n"
        )

        with patch("sebba_code.constants.get_agent_dir", return_value=self.agent_dir):
            from sebba_code.llm import _get_cheap_llm_config
            model, provider, base_url, api_key = _get_cheap_llm_config()

            self.assertEqual(model, "custom-cheap-model")
            self.assertEqual(provider, "openai")
            self.assertEqual(base_url, "https://api.example.com")
            self.assertEqual(api_key, "sk-test123")

    def test_cheap_config_yaml_overrides_env(self):
        """yaml values should override environment variables."""
        _clear_llm_env()
        config_yaml = self.agent_dir / "config.yaml"
        config_yaml.write_text(
            "llm:\n"
            "  cheap_model: yaml-cheap-model\n"
        )
        os.environ["SEBBA_CHEAP_MODEL"] = "env-cheap-model"

        with patch("sebba_code.constants.get_agent_dir", return_value=self.agent_dir):
            from sebba_code.llm import _get_cheap_llm_config
            model, _, _, _ = _get_cheap_llm_config()

            # yaml takes precedence over env
            self.assertEqual(model, "yaml-cheap-model")

    def test_cheap_config_env_used_when_no_yaml(self):
        """Environment variables are used when no yaml config exists."""
        _clear_llm_env()
        os.environ["SEBBA_CHEAP_MODEL"] = "env-cheap-model"

        with patch("sebba_code.constants.get_agent_dir", return_value=self.agent_dir):
            from sebba_code.llm import _get_cheap_llm_config
            model, _, _, _ = _get_cheap_llm_config()

            self.assertEqual(model, "env-cheap-model")

    def test_cheap_config_default_when_no_yaml_no_env(self):
        """Hardcoded defaults are used when no config.yaml and no env vars."""
        _clear_llm_env()

        with patch("sebba_code.constants.get_agent_dir", return_value=self.agent_dir):
            from sebba_code.llm import _get_cheap_llm_config
            model, provider, base_url, api_key = _get_cheap_llm_config()

            self.assertEqual(model, "claude-haiku-4-5-20251001")
            self.assertEqual(provider, "")
            self.assertEqual(base_url, "")
            self.assertEqual(api_key, "")


class TestGetMainLlmConfig(TestCase):
    """Test that _get_main_llm_config reads from config, env, then defaults.

    Precedence order (highest to lowest):
    1. config.yaml values (highest priority)
    2. Environment variables
    3. Hardcoded defaults (lowest priority)
    """

    def setUp(self):
        _clear_llm_env()
        self.agent_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.agent_dir, ignore_errors=True)
        _clear_llm_env()
        from sebba_code import llm
        llm.reset_llm_clients()

    def test_main_config_from_yaml(self):
        """Verify main model is read from config.yaml (yaml has highest priority)."""
        config_yaml = self.agent_dir / "config.yaml"
        config_yaml.write_text(
            "llm:\n"
            "  model: custom-main-model\n"
            "  model_provider: anthropic\n"
            "  base_url: https://api.anthropic.com\n"
            "  api_key: sk-ant-test456\n"
        )

        with patch("sebba_code.constants.get_agent_dir", return_value=self.agent_dir):
            from sebba_code.llm import _get_main_llm_config
            model, provider, base_url, api_key = _get_main_llm_config()

            self.assertEqual(model, "custom-main-model")
            self.assertEqual(provider, "anthropic")
            self.assertEqual(base_url, "https://api.anthropic.com")
            self.assertEqual(api_key, "sk-ant-test456")

    def test_main_config_yaml_overrides_env(self):
        """yaml values should override environment variables."""
        _clear_llm_env()
        config_yaml = self.agent_dir / "config.yaml"
        config_yaml.write_text(
            "llm:\n"
            "  model: yaml-main-model\n"
        )
        os.environ["SEBBA_MODEL"] = "env-main-model"

        with patch("sebba_code.constants.get_agent_dir", return_value=self.agent_dir):
            from sebba_code.llm import _get_main_llm_config
            model, _, _, _ = _get_main_llm_config()

            # yaml takes precedence over env
            self.assertEqual(model, "yaml-main-model")


class TestGetCheapLlmIntegration(TestCase):
    """Integration tests for get_cheap_llm with config."""

    def setUp(self):
        _clear_llm_env()
        self.agent_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.agent_dir, ignore_errors=True)
        _clear_llm_env()
        from sebba_code import llm
        llm.reset_llm_clients()

    def test_get_cheap_llm_uses_config_model(self):
        """get_cheap_llm should use the model from config.yaml when available."""
        config_yaml = self.agent_dir / "config.yaml"
        config_yaml.write_text(
            "llm:\n"
            "  cheap_model: test-cheap-model\n"
        )

        with patch("sebba_code.constants.get_agent_dir", return_value=self.agent_dir):
            with patch("sebba_code.llm._build_llm") as mock_build:
                mock_build.return_value = MagicMock()
                from sebba_code import llm
                llm.reset_llm_clients()

                llm.get_cheap_llm()

                mock_build.assert_called_once()
                call_kwargs = mock_build.call_args[1]
                self.assertEqual(call_kwargs.get("model"), "test-cheap-model")


class TestLLMConfigClass(TestCase):
    """Tests for LLMConfig dataclass."""

    def test_llm_config_defaults(self):
        """Verify LLMConfig has expected default values."""
        from sebba_code.config import LLMConfig

        cfg = LLMConfig()
        # Check that cheap_model-related fields exist
        self.assertTrue(hasattr(cfg, "cheap_model"))
        self.assertTrue(hasattr(cfg, "cheap_model_provider"))
        self.assertTrue(hasattr(cfg, "cheap_base_url"))
        self.assertTrue(hasattr(cfg, "cheap_api_key"))

    def test_llm_config_accepts_cheap_model(self):
        """LLMConfig should accept cheap_model values."""
        from sebba_code.config import LLMConfig

        cfg = LLMConfig(
            cheap_model="my-cheap-model",
            cheap_model_provider="openai",
        )
        self.assertEqual(cfg.cheap_model, "my-cheap-model")
        self.assertEqual(cfg.cheap_model_provider, "openai")
