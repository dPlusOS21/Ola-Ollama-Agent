import hashlib
import json
import math
import os
from pathlib import Path


# Single, global knowledge base shared across all projects/cwds.
# Keeps things predictable: indexing a folder once means it is known
# regardless of where `ola` is launched from.
_GLOBAL_DIR = Path.home() / ".ollama_agent" / "knowledge" / "global"
_GLOBAL_STORE = _GLOBAL_DIR / "store.json"


def _empty_store() -> dict:
    return {"sources": [], "chunks": [], "fingerprints": {}}


def _migrate_legacy_kbs() -> dict | None:
    """Merge any legacy per-cwd KBs into a single global store.

    Runs only if the global store does not yet exist. Returns the merged data
    if migration happened, otherwise None.
    """
    if _GLOBAL_STORE.exists():
        return None

    kb_root = Path.home() / ".ollama_agent" / "knowledge"
    if not kb_root.exists():
        return None

    legacy_dirs = [
        d for d in kb_root.iterdir()
        if d.is_dir() and d.name != "global" and (d / "store.json").exists()
    ]
    if not legacy_dirs:
        return None

    merged = _empty_store()
    seen_sources: set[str] = set()

    for d in legacy_dirs:
        try:
            data = json.loads((d / "store.json").read_text(encoding="utf-8"))
        except Exception:
            continue

        # Merge sources (dedup)
        for s in data.get("sources", []):
            if s not in seen_sources:
                merged["sources"].append(s)
                seen_sources.add(s)

        # Merge chunks (append all — dedup would require re-embedding)
        merged["chunks"].extend(data.get("chunks", []))

        # Merge fingerprints (last one wins)
        merged["fingerprints"].update(data.get("fingerprints", {}))

    # Persist the migrated store
    _GLOBAL_DIR.mkdir(parents=True, exist_ok=True)
    _GLOBAL_STORE.write_text(json.dumps(merged, ensure_ascii=False), encoding="utf-8")

    # Archive legacy dirs so the user can recover them if something went wrong
    archive_root = kb_root / "_legacy_archive"
    archive_root.mkdir(parents=True, exist_ok=True)
    for d in legacy_dirs:
        try:
            target = archive_root / d.name
            if not target.exists():
                d.rename(target)
        except Exception:
            pass

    return merged


def load(cwd: str | None = None) -> dict:
    """Load the global knowledge base.

    The ``cwd`` argument is accepted for backwards compatibility but ignored —
    the KB is now global.
    """
    migrated = _migrate_legacy_kbs()
    if migrated is not None:
        return migrated

    if _GLOBAL_STORE.exists():
        try:
            data = json.loads(_GLOBAL_STORE.read_text(encoding="utf-8"))
            # Ensure all expected keys exist
            if "fingerprints" not in data:
                data["fingerprints"] = {}
            if "sources" not in data:
                data["sources"] = []
            if "chunks" not in data:
                data["chunks"] = []
            return data
        except Exception:
            pass
    return _empty_store()


def save(cwd: str | None, data: dict) -> None:
    """Save the global knowledge base. ``cwd`` is ignored (kept for compat)."""
    _GLOBAL_DIR.mkdir(parents=True, exist_ok=True)
    _GLOBAL_STORE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    return dot / (mag_a * mag_b) if mag_a and mag_b else 0.0


def top_k(data: dict, query_embedding: list[float], k: int = 5) -> list[dict]:
    scored = [
        (cosine_similarity(query_embedding, c["embedding"]), c)
        for c in data["chunks"]
    ]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:k]]
