"""Session persistence: save, list and resume conversations."""

import json
import os
import re
from datetime import datetime
from pathlib import Path

SESSIONS_DIR = Path.home() / ".ollama_agent" / "sessions"


def _generate_title(messages: list[dict]) -> str:
    """Extract a title from the first user message."""
    for m in messages:
        if m.get("role") != "user":
            continue
        content = m.get("content", "")
        if isinstance(content, list):
            # Multimodal message — find the text part
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    content = part["text"]
                    break
            else:
                continue
        if not isinstance(content, str) or not content.strip():
            continue
        text = content.strip().replace("\n", " ")
        if len(text) > 60:
            text = text[:57].rsplit(" ", 1)[0] + "..."
        return text
    return "untitled"


def _slugify(text: str) -> str:
    """Filesystem-safe slug from a title."""
    s = text.lower()
    s = re.sub(r"[^a-z0-9àèéìòù]+", "-", s)
    s = s.strip("-")
    return s[:50] if s else "session"


def save_session(agent, title: str | None = None) -> Path:
    """Save the current conversation to disk. Returns the file path."""
    ts = datetime.now()
    if title is None:
        title = _generate_title(agent.messages)

    filename = f"{_slugify(title)}_{ts.strftime('%Y%m%d_%H%M%S')}.json"

    data = {
        "title": title,
        "cwd": os.getcwd(),
        "model": agent.config.model,
        "provider": agent.config.provider,
        "timestamp": ts.isoformat(),
        "message_count": max(0, len(agent.messages) - 2),
        "messages": agent.messages,
    }

    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = SESSIONS_DIR / filename
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def list_sessions() -> list[dict]:
    """Return session metadata sorted by date (most recent first)."""
    if not SESSIONS_DIR.exists():
        return []

    sessions = []
    for f in SESSIONS_DIR.glob("*.json"):
        try:
            raw = json.loads(f.read_text(encoding="utf-8"))
            meta = {k: v for k, v in raw.items() if k != "messages"}
            meta["_path"] = str(f)
            sessions.append(meta)
        except Exception:
            continue

    sessions.sort(key=lambda s: s.get("timestamp", ""), reverse=True)
    for i, s in enumerate(sessions, 1):
        s["index"] = i
    return sessions


def load_session(index: int | None = None) -> dict | None:
    """Load a session by 1-based index. None or 0 loads the most recent."""
    sessions = list_sessions()
    if not sessions:
        return None

    idx = (index or 1) - 1
    if idx < 0 or idx >= len(sessions):
        return None

    path = sessions[idx]["_path"]
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None
