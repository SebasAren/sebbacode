"""Configuration dataclasses and YAML loading for the agent."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class LoadingConfig:
    l0_max_tokens: int = 500
    l1_max_tokens: int = 2000
    l2_max_tokens: int = 4000
    max_total_context: int = 12000


@dataclass
class RulesConfig:
    global_rules_dir: str = ".agent/rules"
    per_app_rules: bool = True


@dataclass
class GCCConfig:
    max_main_md_lines: int = 60
    k: int = 1
    archive_on_complete: bool = True
    worktrees_dir: str = ".agent/worktrees"
    cleanup_worktrees_on_adopt: bool = True


@dataclass
class ExplorerConfig:
    bootstrap_on_empty: bool = True
    validate_new_roadmaps: bool = True
    recon_before_todo: bool = True
    max_file_read_size: int = 5000
    trace_import_depth: int = 1
    include_git_history: bool = True


@dataclass
class SessionsConfig:
    auto_extract: bool = True
    retention_days: int = 30
    extract_rules: bool = True


@dataclass
class RetrievalConfig:
    strategy: str = "llm"
    git_log_depth: int = 20


@dataclass
class ExecutionConfig:
    max_todos_per_session: int = 5
    max_tool_calls_per_todo: int = 50


@dataclass
class PlanningConfig:
    max_iterations: int = 3
    model: str = ""
    auto_approve: bool = False


@dataclass
class LLMConfig:
    model: str = ""
    model_provider: str = ""
    base_url: str = ""
    api_key: str = ""
    cheap_model: str = ""
    cheap_model_provider: str = ""
    cheap_base_url: str = ""
    cheap_api_key: str = ""

    def __post_init__(self):
        """Fall back to env vars, then hardcoded defaults."""
        import os

        defaults = {
            "model": ("SEBBA_MODEL", "claude-sonnet-4-6"),
            "model_provider": ("SEBBA_MODEL_PROVIDER", ""),
            "base_url": ("SEBBA_BASE_URL", ""),
            "api_key": ("SEBBA_API_KEY", ""),
            "cheap_model": ("SEBBA_CHEAP_MODEL", "claude-haiku-4-5-20251001"),
            "cheap_model_provider": ("SEBBA_CHEAP_MODEL_PROVIDER", ""),
            "cheap_base_url": ("SEBBA_CHEAP_BASE_URL", ""),
            "cheap_api_key": ("SEBBA_CHEAP_API_KEY", ""),
        }
        for attr, (env_var, default) in defaults.items():
            if not getattr(self, attr):
                setattr(self, attr, os.environ.get(env_var, default))


@dataclass
class AgentConfig:
    loading: LoadingConfig = field(default_factory=LoadingConfig)
    rules: RulesConfig = field(default_factory=RulesConfig)
    gcc: GCCConfig = field(default_factory=GCCConfig)
    explorer: ExplorerConfig = field(default_factory=ExplorerConfig)
    sessions: SessionsConfig = field(default_factory=SessionsConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    planning: PlanningConfig = field(default_factory=PlanningConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)


def load_config(agent_dir: Path) -> AgentConfig:
    """Load config from .agent/config.yaml, falling back to defaults."""
    config_path = agent_dir / "config.yaml"
    if not config_path.exists():
        return AgentConfig()

    with open(config_path) as f:
        raw = yaml.safe_load(f) or {}

    config = AgentConfig()
    for section_name, section_cls in [
        ("loading", LoadingConfig),
        ("rules", RulesConfig),
        ("gcc", GCCConfig),
        ("explorer", ExplorerConfig),
        ("sessions", SessionsConfig),
        ("retrieval", RetrievalConfig),
        ("execution", ExecutionConfig),
        ("planning", PlanningConfig),
        ("llm", LLMConfig),
    ]:
        if section_name in raw and isinstance(raw[section_name], dict):
            section = section_cls(**{
                k: v
                for k, v in raw[section_name].items()
                if k in section_cls.__dataclass_fields__
            })
            setattr(config, section_name, section)

    return config
