"""Per-provider/model cost estimation.

Prices are in USD per 1M tokens and reflect public list prices at the time
of writing. Ollama local models are free. Prices can be overridden via
~/.ollama_agent_prices.json with the same structure as PRICES.
"""
from __future__ import annotations

import json
from pathlib import Path


# price = (input_per_1M_usd, output_per_1M_usd)
# Conservative defaults; users can override via ~/.ollama_agent_prices.json
PRICES: dict[str, dict[str, tuple[float, float]]] = {
    "ollama": {
        # Local models — no cost
        "*": (0.0, 0.0),
    },
    "openai": {
        "gpt-4o":              (2.50, 10.00),
        "gpt-4o-mini":         (0.15,  0.60),
        "gpt-4.1":             (2.00,  8.00),
        "gpt-4.1-mini":        (0.40,  1.60),
        "gpt-4.1-nano":        (0.10,  0.40),
        "o1":                  (15.00, 60.00),
        "o1-mini":             (3.00, 12.00),
        "o3-mini":             (1.10,  4.40),
        "*":                   (2.50, 10.00),  # generic fallback
    },
    "groq": {
        "llama-3.3-70b-versatile":   (0.59,  0.79),
        "llama-3.1-8b-instant":      (0.05,  0.08),
        "llama-3.1-70b-versatile":   (0.59,  0.79),
        "mixtral-8x7b-32768":        (0.24,  0.24),
        "gemma2-9b-it":              (0.20,  0.20),
        "*":                         (0.50,  0.70),
    },
    "openrouter": {
        # OpenRouter prices vary; these are indicative for common routes
        "anthropic/claude-3.5-sonnet":     (3.00, 15.00),
        "anthropic/claude-3.5-haiku":      (1.00,  5.00),
        "anthropic/claude-3.7-sonnet":     (3.00, 15.00),
        "anthropic/claude-sonnet-4":       (3.00, 15.00),
        "openai/gpt-4o":                   (2.50, 10.00),
        "openai/gpt-4o-mini":              (0.15,  0.60),
        "google/gemini-2.0-flash-001":     (0.10,  0.40),
        "google/gemini-pro-1.5":           (1.25,  5.00),
        "meta-llama/llama-3.3-70b-instruct": (0.12, 0.30),
        "deepseek/deepseek-chat":          (0.14,  0.28),
        "*":                               (1.50,  5.00),
    },
}


_OVERRIDE_FILE = Path.home() / ".ollama_agent_prices.json"


def _load_overrides() -> dict:
    try:
        return json.loads(_OVERRIDE_FILE.read_text())
    except Exception:
        return {}


def lookup_price(provider: str, model: str) -> tuple[float, float]:
    """Return (input_usd_per_1M, output_usd_per_1M) for a provider/model.

    Falls back to the provider "*" entry if the specific model is unknown,
    then to (0.0, 0.0) if the provider itself is unknown.
    """
    overrides = _load_overrides()
    pr_map = overrides.get(provider) or PRICES.get(provider) or {}
    if model in pr_map:
        return tuple(pr_map[model])  # type: ignore[return-value]
    if "*" in pr_map:
        return tuple(pr_map["*"])  # type: ignore[return-value]
    return (0.0, 0.0)


def estimate_cost(provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate total cost in USD for a given token usage."""
    pin, pout = lookup_price(provider, model)
    return (input_tokens / 1_000_000.0) * pin + (output_tokens / 1_000_000.0) * pout


def fmt_usd(amount: float) -> str:
    """Format a USD amount with sensible precision for small values."""
    if amount == 0:
        return "$0.0000"
    if amount < 0.01:
        return f"${amount:.4f}"
    if amount < 1:
        return f"${amount:.3f}"
    return f"${amount:.2f}"
