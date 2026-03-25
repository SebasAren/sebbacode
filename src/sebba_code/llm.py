"""LLM client initialization and configuration."""

import os

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

_llm: BaseChatModel | None = None
_cheap_llm: BaseChatModel | None = None


def _build_llm(
    model: str,
    model_provider: str = "",
    base_url: str = "",
    api_key: str = "",
) -> BaseChatModel:
    """Build an LLM instance with optional provider, base URL, and API key."""
    kwargs: dict = {}
    if model_provider:
        kwargs["model_provider"] = model_provider
    if base_url:
        kwargs["base_url"] = base_url
    if api_key:
        kwargs["api_key"] = api_key
    return init_chat_model(model, **kwargs)


def get_llm(model: str | None = None) -> BaseChatModel:
    """Get the primary LLM instance."""
    global _llm
    if model:
        return _build_llm(model)
    if _llm is None:
        _llm = _build_llm(
            model=os.environ.get("SEBBA_MODEL", "claude-sonnet-4-6"),
            model_provider=os.environ.get("SEBBA_MODEL_PROVIDER", ""),
            base_url=os.environ.get("SEBBA_BASE_URL", ""),
            api_key=os.environ.get("SEBBA_API_KEY", ""),
        )
    return _llm


def get_cheap_llm(model: str | None = None) -> BaseChatModel:
    """Get a cheaper/faster LLM for low-stakes calls."""
    global _cheap_llm
    if model:
        return _build_llm(model)
    if _cheap_llm is None:
        _cheap_llm = _build_llm(
            model=os.environ.get("SEBBA_CHEAP_MODEL", "claude-haiku-4-5-20251001"),
            model_provider=os.environ.get("SEBBA_CHEAP_MODEL_PROVIDER", ""),
            base_url=os.environ.get("SEBBA_CHEAP_BASE_URL", ""),
            api_key=os.environ.get("SEBBA_CHEAP_API_KEY", ""),
        )
    return _cheap_llm


def configure_llm(
    model: str,
    model_provider: str = "",
    base_url: str = "",
    api_key: str = "",
    cheap_model: str | None = None,
    cheap_model_provider: str = "",
    cheap_base_url: str = "",
    cheap_api_key: str = "",
) -> None:
    """Configure the LLM instances from config."""
    global _llm, _cheap_llm
    _llm = _build_llm(model, model_provider, base_url, api_key)
    if cheap_model:
        _cheap_llm = _build_llm(
            cheap_model, cheap_model_provider, cheap_base_url, cheap_api_key
        )
