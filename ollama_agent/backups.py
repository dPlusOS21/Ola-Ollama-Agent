"""File-edit backup stack used by the /undo command.

Every call to write_file / edit_file pushes a backup of the previous state
onto a stack stored under ~/.ollama_agent_backups/. /undo pops the most
recent backup and restores the original file.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
import uuid
from pathlib import Path


_BACKUP_ROOT = Path.home() / ".ollama_agent_backups"
_INDEX_FILE = _BACKUP_ROOT / "index.json"

# Per-process session id so concurrent ola instances don't mix their stacks
_SESSION_ID = os.getenv("OLLAMA_AGENT_SESSION_ID") or uuid.uuid4().hex[:8]

# Cap the history so the backup folder doesn't grow forever
_MAX_ENTRIES_PER_SESSION = 100


def _load_index() -> dict:
    try:
        return json.loads(_INDEX_FILE.read_text())
    except Exception:
        return {}


def _save_index(data: dict) -> None:
    try:
        _BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
        _INDEX_FILE.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


def _session_stack(index: dict) -> list[dict]:
    return index.setdefault("sessions", {}).setdefault(_SESSION_ID, [])


def _safe_name(path: str) -> str:
    h = hashlib.sha1(path.encode("utf-8")).hexdigest()[:10]
    base = Path(path).name.replace("/", "_")[:40] or "file"
    # Nonce to disambiguate backups that land in the same second for the same path
    nonce = uuid.uuid4().hex[:8]
    return f"{int(time.time())}_{nonce}_{h}_{base}"


def record_backup(path: str, op: str) -> None:
    """Back up the current state of `path` before `op` overwrites it.

    op is one of: "write_file", "edit_file".
    If the file does not exist yet, we record a 'create' marker so /undo
    can delete the file to restore the pre-op state.
    """
    try:
        p = Path(path).resolve()
        _BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
        index = _load_index()
        stack = _session_stack(index)

        entry: dict = {
            "path": str(p),
            "op": op,
            "timestamp": time.time(),
        }

        if p.exists() and p.is_file():
            backup_name = _safe_name(str(p))
            backup_path = _BACKUP_ROOT / backup_name
            shutil.copy2(p, backup_path)
            entry["backup"] = str(backup_path)
            entry["existed"] = True
        else:
            entry["existed"] = False

        stack.append(entry)

        # Trim oldest entries past the cap
        while len(stack) > _MAX_ENTRIES_PER_SESSION:
            oldest = stack.pop(0)
            bp = oldest.get("backup")
            if bp:
                try:
                    Path(bp).unlink(missing_ok=True)
                except Exception:
                    pass

        _save_index(index)
    except Exception:
        # Never let a backup failure break the actual write
        pass


def undo_last() -> tuple[bool, str]:
    """Pop and restore the most recent backup.

    Returns (ok, message). If nothing to undo, ok is False.
    """
    index = _load_index()
    stack = _session_stack(index)
    if not stack:
        return False, "Nessuna operazione da annullare in questa sessione."

    entry = stack.pop()
    _save_index(index)

    path = Path(entry["path"])
    op = entry.get("op", "?")

    try:
        if not entry.get("existed", False):
            # File was created by the op — delete it to restore original state
            if path.exists():
                path.unlink()
            return True, f"Ripristinato ({op}): eliminato {path} (file creato dall'operazione)"

        backup = entry.get("backup")
        if not backup or not Path(backup).exists():
            return False, f"Backup mancante per {path}: impossibile ripristinare."

        shutil.copy2(backup, path)
        try:
            Path(backup).unlink(missing_ok=True)
        except Exception:
            pass
        return True, f"Ripristinato ({op}): {path}"
    except Exception as e:
        return False, f"Errore durante il ripristino di {path}: {e}"


def peek_last() -> dict | None:
    """Return the most recent backup entry without popping it."""
    index = _load_index()
    stack = _session_stack(index)
    return stack[-1] if stack else None


def stack_size() -> int:
    index = _load_index()
    return len(_session_stack(index))
