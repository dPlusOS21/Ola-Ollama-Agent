import hashlib
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from openai import OpenAI

from .chunker import chunk_file, iter_files
from . import store as store_module

# Ollama local is always used for embeddings so data stays on the machine.
# Use a longer pool of HTTP connections so concurrent requests don't queue.
import httpx as _httpx
_EMBED_CLIENT = OpenAI(
    api_key="ollama",
    base_url="http://localhost:11434/v1",
    http_client=_httpx.Client(
        limits=_httpx.Limits(max_connections=32, max_keepalive_connections=32),
        timeout=_httpx.Timeout(120.0, connect=10.0),
    ),
)

# Default number of concurrent embed requests sent to Ollama. Ollama processes
# requests in parallel up to OLLAMA_NUM_PARALLEL (default 4 in recent versions);
# sending more than that just queues server-side, so 4 is a safe default.
_DEFAULT_PARALLEL = int(os.getenv("OLLAMA_AGENT_EMBED_PARALLEL", "4"))


class Retriever:
    _DEFAULT_MODEL = "granite-embedding:30m"

    def __init__(self, embed_model: str | None = None):
        self.embed_model = embed_model or self._DEFAULT_MODEL
        self.cwd = os.getcwd()
        # KB is now global — cwd is kept for legacy API compatibility only
        self._data = store_module.load()
        if "fingerprints" not in self._data:
            self._data["fingerprints"] = {}
        # Detect model change: if the KB was built with a different model,
        # embeddings are incompatible and must be re-indexed.
        # Legacy KBs without embed_model were built with nomic-embed-text.
        stored_model = self._data.get("embed_model") or (
            "nomic-embed-text" if self._data.get("chunks") else None
        )
        if stored_model and stored_model != self.embed_model and self._data["chunks"]:
            self._model_mismatch = stored_model
        else:
            self._model_mismatch = None

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------

    @staticmethod
    def _ensure_model_pulled(model: str) -> None:
        """Pull the embedding model if it is not already available locally."""
        import subprocess
        try:
            result = subprocess.run(
                ["ollama", "show", model],
                capture_output=True, timeout=10,
            )
            if result.returncode == 0:
                return  # already available
        except Exception:
            pass
        # Model not found — pull it
        subprocess.run(
            ["ollama", "pull", model],
            timeout=300,
        )

    def _embed(self, text: str) -> list[float]:
        # granite-embedding:30m and other small models have 512 token context;
        # cap input to ~1200 chars to stay within that limit.
        cap = 8000 if "nomic" in self.embed_model else 1200
        response = _EMBED_CLIENT.embeddings.create(
            model=self.embed_model,
            input=text[:cap],
        )
        return response.data[0].embedding

    def _embed_parallel(
        self,
        texts: list[str],
        max_workers: int = _DEFAULT_PARALLEL,
        on_done: Callable[[], None] | None = None,
    ) -> list[list[float] | None]:
        """Embed many texts via concurrent requests to Ollama.

        Ollama serializes the *contents* of a single batched request, so the
        only way to actually use multiple CPU threads is to fire several HTTP
        requests in parallel. With ``OLLAMA_NUM_PARALLEL`` set on the Ollama
        side (default 4), this gives a near-linear speedup up to that cap.

        Order is preserved in the returned list. Failed individual embeddings
        are returned as ``None`` so the caller can decide how to handle them.
        ``on_done`` is invoked once per completed embedding (thread-safe via
        an internal lock) — useful for driving a progress bar.
        """
        if not texts:
            return []

        results: list[list[float] | None] = [None] * len(texts)
        cb_lock = threading.Lock()

        def worker(i: int) -> None:
            try:
                results[i] = self._embed(texts[i])
            except Exception:
                results[i] = None
            if on_done is not None:
                with cb_lock:
                    on_done()

        with ThreadPoolExecutor(max_workers=max(1, max_workers)) as ex:
            # Drain results so exceptions inside workers surface
            list(ex.map(worker, range(len(texts))))

        return results

    # ------------------------------------------------------------------
    # File fingerprinting
    # ------------------------------------------------------------------

    @staticmethod
    def _file_hash(path: Path) -> str:
        """Fast content hash for change detection."""
        h = hashlib.md5()
        try:
            h.update(path.read_bytes())
        except Exception:
            return ""
        return h.hexdigest()

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def index(
        self,
        path: str,
        progress_cb: Callable[[str, int, int, int, int], None] | None = None,
        scan_cb: Callable[[int, int, int], None] | None = None,
        force: bool = False,
        parallel_workers: int | None = None,
    ) -> tuple[int, int]:
        """Index a file or directory. Returns (files_indexed, chunks_added).

        Only new or modified files are re-embedded. Deleted files are purged.
        If ``force=True``, all files under ``path`` are re-embedded regardless
        of their stored fingerprints (useful after chunker improvements).

        Embeddings for each file are computed by firing ``parallel_workers``
        concurrent requests to Ollama (default from
        ``OLLAMA_AGENT_EMBED_PARALLEL`` env var, fallback 4). Make sure
        ``OLLAMA_NUM_PARALLEL`` is at least as high on the Ollama side.

        ``progress_cb`` receives ``(filename, chunks_done_total,
        chunks_total, in_file_done, in_file_total)`` and is called once at the
        start of each file (with ``in_file_done=0``) and after every embedded
        chunk. ``chunks_total`` is the total across all files to index, so it
        can drive a single progress bar with chunk-level granularity.

        ``scan_cb`` receives ``(total_on_disk, new_count, modified_count)``.
        """
        if parallel_workers is None:
            parallel_workers = _DEFAULT_PARALLEL

        # Auto-pull the embedding model on first use
        self._ensure_model_pulled(self.embed_model)

        # If the model changed, clear old (incompatible) embeddings
        stored_model = self._data.get("embed_model")
        if stored_model and stored_model != self.embed_model and self._data["chunks"]:
            self._data["chunks"] = []
            self._data["fingerprints"] = {}
            # Keep sources list so we know what was indexed before
            force = True  # must re-embed everything

        p = Path(path)
        files = list(iter_files(p))
        current_paths = {str(f.resolve()) for f in files}

        # Ensure the fingerprints dict exists (migration for old stores)
        if "fingerprints" not in self._data:
            self._data["fingerprints"] = {}

        stored_fp: dict[str, str] = self._data["fingerprints"]

        # Migration: backfill fingerprints for files already in sources but missing from fingerprints
        existing_sources = set(self._data.get("sources", []))
        for src in existing_sources:
            if src not in stored_fp:
                p_src = Path(src)
                if p_src.exists():
                    stored_fp[src] = self._file_hash(p_src)

        # Classify files: new, modified, or unchanged
        to_index: list[Path] = []
        new_count = 0
        modified_count = 0

        for f in files:
            src = str(f.resolve())
            fp = self._file_hash(f)
            if force:
                # Force re-index everything under this path
                to_index.append(f)
                if src in stored_fp:
                    modified_count += 1
                else:
                    new_count += 1
            elif src not in stored_fp:
                to_index.append(f)
                new_count += 1
            elif stored_fp[src] != fp:
                to_index.append(f)
                modified_count += 1
            # else: unchanged — skip

        # Purge chunks for files that no longer exist on disk
        deleted = set(stored_fp.keys()) - current_paths
        if deleted:
            self._data["chunks"] = [
                c for c in self._data["chunks"] if c["source"] not in deleted
            ]
            self._data["sources"] = [
                s for s in self._data["sources"] if s not in deleted
            ]
            for d in deleted:
                del stored_fp[d]

        if scan_cb:
            scan_cb(len(files), new_count, modified_count)

        # Pre-chunk every file (chunking is fast and CPU-only) so we know the
        # total chunk count up front and can drive a chunk-granularity bar.
        pending: list[tuple[Path, list[dict]]] = []
        total_chunks_pending = 0
        for f in to_index:
            try:
                chunks = chunk_file(f)
            except Exception:
                chunks = []
            pending.append((f, chunks))
            total_chunks_pending += len(chunks)

        files_done = 0
        chunks_done = 0
        chunks_done_global = 0

        for f, chunks in pending:
            src = str(f.resolve())
            in_file_total = len(chunks)

            # Signal start of file with 0 progress so the bar shows the
            # filename immediately even before the first chunk completes.
            if progress_cb:
                progress_cb(f.name, chunks_done_global, total_chunks_pending, 0, in_file_total)

            # Empty/unparseable file: still mark it as processed so we
            # don't re-attempt it on every run.
            if not chunks:
                stored_fp[src] = self._file_hash(f)
                if src not in self._data["sources"]:
                    self._data["sources"].append(src)
                files_done += 1
                store_module.save(None, self._data)
                continue

            texts = [c["text"] for c in chunks]
            in_file_done = 0

            def on_done() -> None:
                # Called from worker threads — already serialized by the
                # lock inside _embed_parallel before being invoked here.
                nonlocal in_file_done, chunks_done_global
                in_file_done += 1
                chunks_done_global += 1
                if progress_cb:
                    progress_cb(
                        f.name,
                        chunks_done_global,
                        total_chunks_pending,
                        in_file_done,
                        in_file_total,
                    )

            embeddings = self._embed_parallel(
                texts, max_workers=parallel_workers, on_done=on_done
            )

            # Build the new chunk records (skip failed embeddings)
            new_chunk_records = [
                {"source": src, "text": chunk["text"], "embedding": emb}
                for chunk, emb in zip(chunks, embeddings)
                if emb is not None
            ]

            if new_chunk_records:
                # Atomic swap: remove old chunks for this src then add new ones.
                # Doing this AFTER embedding succeeds means a Ctrl+C mid-file
                # leaves the previous version intact.
                self._data["chunks"] = [
                    c for c in self._data["chunks"] if c["source"] != src
                ]
                self._data["chunks"].extend(new_chunk_records)
                chunks_done += len(new_chunk_records)

                stored_fp[src] = self._file_hash(f)
                if src not in self._data["sources"]:
                    self._data["sources"].append(src)
                files_done += 1

                # Persist after every file → progress survives a kill / crash
                store_module.save(None, self._data)

        # Record which model produced these embeddings
        self._data["embed_model"] = self.embed_model
        self._model_mismatch = None  # mismatch resolved after successful index
        # Final save in case the loop body never ran (no files to index)
        store_module.save(None, self._data)
        return files_done, chunks_done

    def remove(self, path: str) -> int:
        """Remove a file from the knowledge base. Returns chunks removed."""
        src = str(Path(path).resolve())
        before = len(self._data["chunks"])
        self._data["chunks"] = [c for c in self._data["chunks"] if c["source"] != src]
        self._data["sources"] = [s for s in self._data["sources"] if s != src]
        removed = before - len(self._data["chunks"])
        if removed:
            store_module.save(None, self._data)
        return removed

    def clear(self) -> None:
        self._data = {"sources": [], "chunks": []}
        store_module.save(None, self._data)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        k: int = 5,
        max_chars: int = 6000,
        source_filter: str | None = None,
    ) -> str:
        """Return formatted context for the top-k most relevant chunks.

        If ``source_filter`` is given, only chunks whose source path or filename
        contains that substring (case-insensitive) are considered. Useful when
        the user asks about a specific file by name.

        Results are capped at max_chars to avoid exceeding the model's context window.
        """
        if not self._data["chunks"]:
            return "Knowledge base is empty. Use /learn <path> to index documents."

        if self._model_mismatch:
            return (
                f"The knowledge base was built with '{self._model_mismatch}' but the current "
                f"model is '{self.embed_model}'. Re-index with /learn <path> --force to update."
            )

        # Filter by source path/name if requested
        data = self._data
        if source_filter:
            sf = source_filter.lower().strip()
            filtered = [
                c for c in self._data["chunks"]
                if sf in Path(c["source"]).name.lower() or sf in c["source"].lower()
            ]
            if not filtered:
                available = sorted({Path(s).name for s in self._data["sources"]})
                return (
                    f"No file matching '{source_filter}' found in the knowledge base.\n"
                    f"Available files: {', '.join(available[:20])}"
                    + (f" (+{len(available) - 20} more)" if len(available) > 20 else "")
                )
            data = {"sources": self._data["sources"], "chunks": filtered}
            # Return more chunks when restricted to a specific file so the
            # model can get a broader view for summarization-style questions
            k = max(k, 10)

        try:
            q_emb = self._embed(query)
        except Exception as e:
            return f"Error creating query embedding: {e}"

        results = store_module.top_k(data, q_emb, k=k)
        if not results:
            return "No relevant content found in the knowledge base."

        parts = []
        total_chars = 0
        for r in results:
            label = Path(r["source"]).name
            text = r["text"]
            # Truncate individual chunk if very long
            if len(text) > 1500:
                text = text[:1500] + "\n[... truncated]"
            entry = f"[{label}]\n{text}"
            if total_chars + len(entry) > max_chars:
                parts.append(f"[... {len(results) - len(parts)} more results omitted to fit context]")
                break
            parts.append(entry)
            total_chars += len(entry)
        return "\n\n---\n\n".join(parts)

    # ------------------------------------------------------------------
    # Info
    # ------------------------------------------------------------------

    @property
    def source_count(self) -> int:
        return len(self._data["sources"])

    @property
    def chunk_count(self) -> int:
        return len(self._data["chunks"])

    @property
    def sources(self) -> list[str]:
        return self._data["sources"]
