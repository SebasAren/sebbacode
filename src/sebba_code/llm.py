"""LLM client initialization and configuration."""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

logger = logging.getLogger("sebba_code")

_llm: BaseChatModel | None = None
_cheap_llm: BaseChatModel | None = None


def _build_llm(
    model: str,
    model_provider: str = "",
    base_url: str = "",
    api_key: str = "",
    timeout: int = 0,
) -> BaseChatModel:
    """Build an LLM instance with optional provider, base URL, and API key."""
    kwargs: dict = {}
    if model_provider:
        kwargs["model_provider"] = model_provider
    if base_url:
        kwargs["base_url"] = base_url
    if api_key:
        kwargs["api_key"] = api_key
    if timeout > 0:
        kwargs["timeout"] = timeout
        kwargs["request_timeout"] = timeout
    return init_chat_model(model, **kwargs)


def _get_llm_timeout() -> int:
    """Get LLM timeout from env or config."""
    env_val = os.environ.get("SEBBA_LLM_TIMEOUT", "")
    if env_val:
        return int(env_val)
    try:
        from sebba_code.config import load_config
        from sebba_code.constants import get_agent_dir
        return load_config(get_agent_dir()).execution.llm_timeout
    except Exception:
        return 120


def _get_cheap_llm_config() -> tuple[str, str, str, str]:
    """Get cheap LLM settings from config, falling back to env vars then defaults.

    Returns a tuple of (model, model_provider, base_url, api_key).
    """
    try:
        from sebba_code.config import load_config
        from sebba_code.constants import get_agent_dir
        cfg = load_config(get_agent_dir()).llm
        return (
            cfg.cheap_model,
            cfg.cheap_model_provider,
            cfg.cheap_base_url,
            cfg.cheap_api_key,
        )
    except Exception:
        pass

    # Fall back to environment variables
    return (
        os.environ.get("SEBBA_CHEAP_MODEL", "claude-haiku-4-5-20251001"),
        os.environ.get("SEBBA_CHEAP_MODEL_PROVIDER", ""),
        os.environ.get("SEBBA_CHEAP_BASE_URL", ""),
        os.environ.get("SEBBA_CHEAP_API_KEY", ""),
    )


def _get_main_llm_config() -> tuple[str, str, str, str]:
    """Get main LLM settings from config, falling back to env vars then defaults.

    Returns a tuple of (model, model_provider, base_url, api_key).
    """
    try:
        from sebba_code.config import load_config
        from sebba_code.constants import get_agent_dir
        cfg = load_config(get_agent_dir()).llm
        return (
            cfg.model,
            cfg.model_provider,
            cfg.base_url,
            cfg.api_key,
        )
    except Exception:
        pass

    # Fall back to environment variables
    return (
        os.environ.get("SEBBA_MODEL", "claude-sonnet-4-6"),
        os.environ.get("SEBBA_MODEL_PROVIDER", ""),
        os.environ.get("SEBBA_BASE_URL", ""),
        os.environ.get("SEBBA_API_KEY", ""),
    )


def invoke_with_timeout(
    llm: BaseChatModel,
    prompt,
    timeout_seconds: int | None = None,
):
    """Invoke an LLM with a hard Python-level timeout.

    Uses concurrent.futures to enforce the timeout regardless of whether
    the underlying HTTP client respects its own timeout settings.
    """
    if timeout_seconds is None:
        timeout_seconds = _get_llm_timeout()
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(llm.invoke, prompt)
        try:
            return future.result(timeout=timeout_seconds)
        except FuturesTimeoutError:
            logger.warning("LLM call timed out after %ds", timeout_seconds)
            raise TimeoutError(f"LLM call timed out after {timeout_seconds}s")


def get_llm(model: str | None = None) -> BaseChatModel:
    """Get the primary LLM instance.

    Parameters
    ----------
    model:
        Override the model name. If not provided, falls back to config
        then environment variables, then hardcoded defaults.
    """
    global _llm
    if model:
        return _build_llm(model)
    if _llm is None:
        model, model_provider, base_url, api_key = _get_main_llm_config()
        _llm = _build_llm(
            model=model,
            model_provider=model_provider,
            base_url=base_url,
            api_key=api_key,
            timeout=_get_llm_timeout(),
        )
    return _llm


def get_cheap_llm(model: str | None = None) -> BaseChatModel:
    """Get a cheaper/faster LLM for low-stakes calls (e.g., L2→L1 summarisation).

    Parameters
    ----------
    model:
        Override the model name. If not provided, falls back to config
        (llm.cheap_model) then environment variables, then hardcoded defaults.

    The cheap model is used for L2→L1 summarisation and other low-stakes
    operations where model quality is less critical than cost and speed.
    """
    global _cheap_llm
    if model:
        return _build_llm(model)
    if _cheap_llm is None:
        model, model_provider, base_url, api_key = _get_cheap_llm_config()
        _cheap_llm = _build_llm(
            model=model,
            model_provider=model_provider,
            base_url=base_url,
            api_key=api_key,
            timeout=_get_llm_timeout(),
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


def reset_llm_clients() -> None:
    """Reset LLM clients (useful for testing)."""
    global _llm, _cheap_llm
    _llm = None
    _cheap_llm = None
