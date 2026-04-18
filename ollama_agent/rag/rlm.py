"""Recursive Language Model (RLM) retrieval.

Pipeline:
  1. Gather all chunks (optionally filtered by source).
  2. Group chunks by source file.
  3. For each source: if chunks fit in a single LLM call, keep the raw text;
     otherwise split into batches, ask the LLM to extract only the parts
     relevant to the question from each batch (recursion level 1).
  4. Return the condensed, source-tagged context to the caller — the outer
     agent then produces the final answer from it.

Unlike standard top-k retrieval, RLM reads *every* chunk of the selected
documents, delegating relevance filtering to the LLM itself. This preserves
global context at the cost of extra LLM calls.
"""

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


# Rough char budget per LLM summarization call. Small enough to stay well
# within any model's context window, large enough to keep the recursion
# shallow.
_BATCH_CHAR_BUDGET = 12000

# Max chars the final aggregated context is allowed to reach. Beyond this we
# truncate to avoid blowing up the outer agent's context window.
_MAX_OUTPUT_CHARS = 40000


def _join_until_budget(texts: list[str], budget: int) -> list[str]:
    """Group texts into batches, each under ``budget`` chars."""
    batches: list[str] = []
    current: list[str] = []
    size = 0
    for t in texts:
        if size + len(t) > budget and current:
            batches.append("\n\n".join(current))
            current = [t]
            size = len(t)
        else:
            current.append(t)
            size += len(t)
    if current:
        batches.append("\n\n".join(current))
    return batches


def _extract_relevant(client, model: str, question: str, text: str, filename: str) -> str:
    """Ask the LLM to extract only the parts of ``text`` relevant to the question."""
    prompt = (
        f"Hai il seguente estratto dal file '{filename}'.\n"
        f"Domanda dell'utente: {question}\n\n"
        f"Estratto:\n{text}\n\n"
        f"Estrai SOLO le parti dell'estratto che sono direttamente utili a rispondere "
        f"alla domanda. Preserva citazioni e dati numerici. Se nulla è rilevante, "
        f"rispondi esattamente: NESSUNA INFORMAZIONE RILEVANTE."
    )
    try:
        r = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return (r.choices[0].message.content or "").strip()
    except Exception as e:
        return f"[errore RLM su {filename}: {e}]"


def deep_query(
    retriever,
    client,
    model: str,
    question: str,
    source_filter: str | None = None,
    max_workers: int = 4,
) -> str:
    """Recursive retrieval across the knowledge base.

    Returns a condensed, source-tagged context block suitable for direct
    injection into the agent's conversation.
    """
    chunks = retriever._data.get("chunks", [])
    if not chunks:
        return "Knowledge base vuota. Usa /learn <path> per indicizzare."

    if source_filter:
        sf = source_filter.lower().strip()
        chunks = [
            c for c in chunks
            if sf in Path(c["source"]).name.lower() or sf in c["source"].lower()
        ]
        if not chunks:
            return f"Nessun file corrispondente a '{source_filter}'."

    by_src: dict[str, list[str]] = defaultdict(list)
    for c in chunks:
        by_src[c["source"]].append(c["text"])

    # Plan the work: for each source, either keep raw or split into batches
    jobs: list[tuple[str, str, bool]] = []  # (filename, batch_text, needs_llm)
    for src, texts in by_src.items():
        name = Path(src).name
        full = "\n\n".join(texts)
        if len(full) <= _BATCH_CHAR_BUDGET:
            jobs.append((name, full, False))
        else:
            for batch in _join_until_budget(texts, _BATCH_CHAR_BUDGET):
                jobs.append((name, batch, True))

    # Run LLM extractions in parallel
    def process(job: tuple[str, str, bool]) -> tuple[str, str]:
        name, text, needs_llm = job
        if not needs_llm:
            return name, text
        extracted = _extract_relevant(client, model, question, text, name)
        if "NESSUNA INFORMAZIONE RILEVANTE" in extracted.upper():
            return name, ""
        return name, extracted

    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as ex:
        results = list(ex.map(process, jobs))

    # Group results by filename
    by_name: dict[str, list[str]] = defaultdict(list)
    for name, text in results:
        if text:
            by_name[name].append(text)

    if not by_name:
        return "Nessuna informazione rilevante trovata nei documenti indicizzati."

    parts = []
    total = 0
    for name, texts in by_name.items():
        merged = "\n\n".join(texts)
        entry = f"[{name}]\n{merged}"
        if total + len(entry) > _MAX_OUTPUT_CHARS:
            parts.append(f"[... contenuto aggiuntivo troncato per limiti di contesto]")
            break
        parts.append(entry)
        total += len(entry)

    return "\n\n---\n\n".join(parts)
