import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_PREFS_FILE = Path.home() / ".ollama_agent_prefs.json"

# Routing modes
ROUTING_MODES = ("manual", "auto", "static")

# Task categories used by auto-router and static rules
TASK_CATEGORIES = ("code", "debug", "review", "docs", "general")

# Default static rules (task_category → model name)
DEFAULT_STATIC_RULES: dict[str, str] = {
    "code": "deepseek-coder-v2",
    "debug": "deepseek-coder-v2",
    "review": "anthropic/claude-3.5-sonnet",
    "docs": "llama3.1",
    "general": "llama3.1",
}


def load_user_prefs() -> dict:
    try:
        return json.loads(_PREFS_FILE.read_text())
    except Exception:
        return {}


def save_user_prefs(provider: str, model: str) -> None:
    prefs = load_user_prefs()
    prefs["provider"] = provider
    # Store models per-provider so each provider remembers its own model
    models = prefs.get("models", {})
    # Migrate legacy flat "model" key
    if "model" in prefs and not models:
        old_provider = prefs.get("provider", "ollama")
        models[old_provider] = prefs.pop("model")
    elif "model" in prefs:
        prefs.pop("model")
    models[provider] = model
    prefs["models"] = models
    _PREFS_FILE.write_text(json.dumps(prefs, indent=2))


def save_routing_mode(mode: str) -> None:
    prefs = load_user_prefs()
    prefs["routing_mode"] = mode
    _PREFS_FILE.write_text(json.dumps(prefs, indent=2))


def load_routing_mode() -> str:
    prefs = load_user_prefs()
    mode = prefs.get("routing_mode", "manual")
    return mode if mode in ROUTING_MODES else "manual"


def save_static_rules(rules: dict[str, str]) -> None:
    prefs = load_user_prefs()
    prefs["static_rules"] = rules
    _PREFS_FILE.write_text(json.dumps(prefs, indent=2))


def save_auto_save_pref(enabled: bool) -> None:
    prefs = load_user_prefs()
    prefs["auto_save_session"] = enabled
    _PREFS_FILE.write_text(json.dumps(prefs, indent=2))


def load_auto_save_pref() -> bool:
    prefs = load_user_prefs()
    return prefs.get("auto_save_session", False)


def save_quiet_pref(enabled: bool) -> None:
    prefs = load_user_prefs()
    prefs["quiet_mode"] = enabled
    _PREFS_FILE.write_text(json.dumps(prefs, indent=2))


def load_quiet_pref() -> bool:
    prefs = load_user_prefs()
    return prefs.get("quiet_mode", True)


RAG_MODES = ("standard", "rlm")


def save_rag_mode(mode: str) -> None:
    prefs = load_user_prefs()
    prefs["rag_mode"] = mode
    _PREFS_FILE.write_text(json.dumps(prefs, indent=2))


def load_rag_mode() -> str:
    prefs = load_user_prefs()
    mode = prefs.get("rag_mode", "standard")
    return mode if mode in RAG_MODES else "standard"


def save_queue_input_pref(enabled: bool) -> None:
    prefs = load_user_prefs()
    prefs["queue_input"] = enabled
    _PREFS_FILE.write_text(json.dumps(prefs, indent=2))


def load_queue_input_pref() -> bool:
    prefs = load_user_prefs()
    return prefs.get("queue_input", False)


LANGUAGES = ("it", "en")


def save_language(lang: str) -> None:
    prefs = load_user_prefs()
    prefs["language"] = lang
    _PREFS_FILE.write_text(json.dumps(prefs, indent=2))


def load_language() -> str:
    prefs = load_user_prefs()
    lang = prefs.get("language", "it")
    return lang if lang in LANGUAGES else "it"


def load_static_rules() -> dict[str, str]:
    prefs = load_user_prefs()
    saved = prefs.get("static_rules")
    if isinstance(saved, dict) and saved:
        return saved
    return dict(DEFAULT_STATIC_RULES)

PROVIDERS: dict[str, dict] = {
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "default_model": "deepseek-v3.1:671b-cloud",
        "env_key": "OLLAMA_API_KEY",  # not required for local Ollama
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o",
        "env_key": "OPENAI_API_KEY",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "anthropic/claude-3.5-sonnet",
        "env_key": "OPENROUTER_API_KEY",
    },
}


@dataclass
class Config:
    provider: str
    model: str
    api_key: str
    base_url: str

    @classmethod
    def from_env(cls, provider: str = None, model: str = None) -> "Config":
        prefs = load_user_prefs()

        # Priority: explicit arg > env var > saved prefs > default
        if provider is None:
            provider = os.getenv("OLLAMA_CODE_PROVIDER", prefs.get("provider", "ollama"))
        if provider not in PROVIDERS:
            provider = "ollama"

        pconf = PROVIDERS[provider]
        # Ollama local doesn't require an API key; use a placeholder if absent
        api_key = os.getenv(pconf["env_key"], "ollama" if provider == "ollama" else "")
        base_url = os.getenv("OLLAMA_CODE_BASE_URL", pconf["base_url"])
        # Load saved model for this specific provider
        saved_models = prefs.get("models", {})
        # Fallback: legacy flat "model" key
        saved_model = saved_models.get(provider, prefs.get("model", pconf["default_model"]))
        model = model or os.getenv("OLLAMA_CODE_MODEL", saved_model)

        return cls(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
        )
