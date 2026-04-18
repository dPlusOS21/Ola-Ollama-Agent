"""Web search and fetch tools.

Three providers supported:
  - duckduckgo (default, no API key required)
  - brave      (requires BRAVE_API_KEY)
  - tavily     (requires TAVILY_API_KEY)

Graceful degradation: if a provider's dependency is missing or a network
error happens, returns a clear error string — never raises.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

_DEFAULT_TIMEOUT = 15
_MAX_FETCH_CHARS = 20000
_DEFAULT_RESULTS = 5


def _format_results(results: list[dict[str, str]]) -> str:
    """Format search results as compact plain text for the LLM."""
    if not results:
        return "No results found."
    lines: list[str] = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "(no title)").strip()
        url = r.get("url", "").strip()
        snippet = r.get("snippet", "").strip()
        lines.append(f"[{i}] {title}")
        lines.append(f"    {url}")
        if snippet:
            snippet = re.sub(r"\s+", " ", snippet)
            if len(snippet) > 300:
                snippet = snippet[:297] + "..."
            lines.append(f"    {snippet}")
        lines.append("")
    return "\n".join(lines).rstrip()


# ── DuckDuckGo ─────────────────────────────────────────────────────────────

def _search_duckduckgo(query: str, max_results: int) -> str:
    try:
        try:
            from ddgs import DDGS  # newer package name
        except ImportError:
            from duckduckgo_search import DDGS  # legacy name
    except ImportError:
        return (
            "DuckDuckGo search package not installed. "
            "Install with: pip install ddgs"
        )
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", "") or r.get("url", ""),
                    "snippet": r.get("body", "") or r.get("snippet", ""),
                })
        return _format_results(results)
    except Exception as e:
        return f"DuckDuckGo search failed: {e}"


# ── Brave Search ───────────────────────────────────────────────────────────

def _search_brave(query: str, max_results: int) -> str:
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        return (
            "BRAVE_API_KEY not set. Get a free key from "
            "https://brave.com/search/api and export BRAVE_API_KEY=..."
        )
    try:
        import httpx
    except ImportError:
        return "httpx not installed. Install with: pip install httpx"
    try:
        r = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": max_results},
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": api_key,
            },
            timeout=_DEFAULT_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        items = data.get("web", {}).get("results", [])
        results = [{
            "title": it.get("title", ""),
            "url": it.get("url", ""),
            "snippet": it.get("description", ""),
        } for it in items[:max_results]]
        return _format_results(results)
    except Exception as e:
        return f"Brave search failed: {e}"


# ── Tavily ─────────────────────────────────────────────────────────────────

def _search_tavily(query: str, max_results: int) -> str:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return (
            "TAVILY_API_KEY not set. Get a free key from "
            "https://tavily.com and export TAVILY_API_KEY=..."
        )
    try:
        import httpx
    except ImportError:
        return "httpx not installed. Install with: pip install httpx"
    try:
        r = httpx.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": "basic",
            },
            timeout=_DEFAULT_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        items = data.get("results", [])
        results = [{
            "title": it.get("title", ""),
            "url": it.get("url", ""),
            "snippet": it.get("content", ""),
        } for it in items[:max_results]]
        return _format_results(results)
    except Exception as e:
        return f"Tavily search failed: {e}"


# ── Public entry points ────────────────────────────────────────────────────

def web_search(query: str, provider: str = "duckduckgo", max_results: int = _DEFAULT_RESULTS) -> str:
    """Search the web and return formatted results.

    Args:
        query: Free-form search string.
        provider: 'duckduckgo' | 'brave' | 'tavily'.
        max_results: number of results (default 5, clamped to 1..10).
    """
    if not query or not query.strip():
        return "Error: empty query."
    try:
        n = max(1, min(int(max_results), 10))
    except Exception:
        n = _DEFAULT_RESULTS
    provider = (provider or "duckduckgo").lower().strip()
    if provider == "brave":
        return _search_brave(query, n)
    if provider == "tavily":
        return _search_tavily(query, n)
    return _search_duckduckgo(query, n)


def web_fetch(url: str, max_chars: int = _MAX_FETCH_CHARS) -> str:
    """Download a URL and return its main text content as markdown-ish plain text.

    Uses httpx + markdownify when available; falls back to a light HTML strip
    if markdownify is missing.
    """
    if not url or not url.strip():
        return "Error: empty URL."
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return f"Error: URL must start with http:// or https:// (got: {url})"
    try:
        import httpx
    except ImportError:
        return "httpx not installed. Install with: pip install httpx"
    try:
        r = httpx.get(
            url,
            timeout=_DEFAULT_TIMEOUT,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; OlaAgent/0.6) "
                    "Python-httpx"
                )
            },
        )
        r.raise_for_status()
        html = r.text
    except Exception as e:
        return f"Fetch failed: {e}"

    # Try markdownify for nice output
    text: str
    try:
        from markdownify import markdownify as md  # type: ignore
        text = md(html, heading_style="ATX", strip=["script", "style", "noscript"])
    except ImportError:
        # Fallback: strip tags with regex
        text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.S | re.I)
        text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", " ", text)

    # Clean up whitespace, trim
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = text.strip()

    try:
        limit = max(1000, min(int(max_chars), 60000))
    except Exception:
        limit = _MAX_FETCH_CHARS

    if len(text) > limit:
        text = text[:limit] + f"\n\n[... truncated at {limit} characters ...]"
    return f"URL: {url}\n\n{text}"
