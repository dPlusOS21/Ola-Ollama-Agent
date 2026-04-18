import base64
import json
import mimetypes
import os
import re
import subprocess
from pathlib import Path

from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .config import (
    Config, PROVIDERS, TASK_CATEGORIES,
    load_routing_mode, load_static_rules, load_quiet_pref, load_rag_mode,
    load_web_enabled, load_web_provider,
)
from .mcp_client import MCPManager
from .rag.retriever import Retriever
from .tools import TOOL_DEFINITIONS, WEB_TOOL_DEFINITIONS, execute_tool

console = Console()

SYSTEM_PROMPT = """You are Ollama Agent, an AI-powered coding assistant running in the terminal.

You help users with software engineering tasks: writing code, fixing bugs, refactoring, explaining code, and more.

Guidelines:
- Be concise and direct. Lead with the answer.
- Always read files before modifying them.
- Make minimal, targeted changes. Don't refactor beyond what's asked.
- Prefer editing existing files over creating new ones.
- Run tests when available to verify changes.
- Ask for clarification only when truly necessary.

You have access to tools for file operations, bash execution, and code search.

Knowledge base:
- When you use search_knowledge, the returned chunks already contain the extracted text from the original documents.
- NEVER attempt to read knowledge base source files by ANY means — not read_file, not bash (cat, head, tail, strings, less), not any other tool.
- The chunks returned by search_knowledge ARE the content. If the chunks don't answer the question, say so — do NOT try to read the original file.
- If you need more detail, call search_knowledge again with a different query.
- When the user asks about a SPECIFIC file by name (e.g. "di cosa tratta il file X.pdf", "riassumi il documento Rossi.pdf"), you MUST pass the filename (or a distinctive substring of it) as the 'source_filter' argument to search_knowledge. This restricts the search to that specific file only — otherwise results come from any file in the KB and the answer will be wrong.
- Attempting to read a knowledge base file will be automatically blocked.
- When you use information from search_knowledge results, cite the source file inline in your answer using square brackets, e.g. "According to [retriever.py], ...". The filename is the header of each chunk returned by search_knowledge."""


def _build_context_block() -> str:
    """Build a context block with cwd, git info, and OLLAMA.md content."""
    lines: list[str] = []

    cwd = os.getcwd()
    lines.append(f"Working directory: {cwd}")

    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd, stderr=subprocess.DEVNULL, text=True,
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--short"],
            cwd=cwd, stderr=subprocess.DEVNULL, text=True,
        ).strip()
        lines.append(f"Git branch: {branch}")
        if status:
            lines.append(f"Git status:\n{status}")
    except Exception:
        pass

    agent_md = Path(cwd) / "AGENT.md"
    if agent_md.exists():
        content = agent_md.read_text(encoding="utf-8").strip()
        if content:
            lines.append(f"\nProject context (AGENT.md):\n{content}")

    return "\n".join(lines)


_USAGE_FILE = Path.home() / ".ollama_agent_usage.json"

# Default weekly token limit (configurable via OLLAMA_AGENT_WEEKLY_LIMIT env var)
_WEEKLY_LIMIT = int(os.getenv("OLLAMA_AGENT_WEEKLY_LIMIT", "0"))


def _iso_week() -> str:
    """Return current ISO year-week string, e.g. '2026-W14'."""
    from datetime import datetime
    d = datetime.now()
    return f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}"


def _load_weekly_usage() -> dict:
    try:
        data = json.loads(_USAGE_FILE.read_text())
        if data.get("week") != _iso_week():
            return {"week": _iso_week(), "input": 0, "output": 0, "breakdown": {}}
        data.setdefault("breakdown", {})
        return data
    except Exception:
        return {"week": _iso_week(), "input": 0, "output": 0, "breakdown": {}}


def _save_weekly_usage(data: dict) -> None:
    try:
        _USAGE_FILE.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


class Usage:
    def __init__(self):
        self.session_input = 0
        self.session_output = 0
        self.last_input = 0
        self.last_output = 0
        # Per-(provider,model) breakdown for the current session
        self.session_breakdown: dict[str, dict[str, int]] = {}
        self._weekly = _load_weekly_usage()

    def update(self, input_tokens: int, output_tokens: int, provider: str | None = None, model: str | None = None) -> None:
        self.last_input = input_tokens
        self.last_output = output_tokens
        self.session_input += input_tokens
        self.session_output += output_tokens
        # Persist weekly totals
        self._weekly["input"] = self._weekly.get("input", 0) + input_tokens
        self._weekly["output"] = self._weekly.get("output", 0) + output_tokens

        # Per-(provider,model) breakdown (session + weekly)
        if provider and model:
            key = f"{provider}/{model}"
            sb = self.session_breakdown.setdefault(key, {"input": 0, "output": 0})
            sb["input"] += input_tokens
            sb["output"] += output_tokens

            wb = self._weekly.setdefault("breakdown", {})
            entry = wb.setdefault(key, {"input": 0, "output": 0})
            entry["input"] = entry.get("input", 0) + input_tokens
            entry["output"] = entry.get("output", 0) + output_tokens

        _save_weekly_usage(self._weekly)

    @property
    def weekly_breakdown(self) -> dict[str, dict[str, int]]:
        return self._weekly.get("breakdown", {})

    @property
    def session_total(self) -> int:
        return self.session_input + self.session_output

    @property
    def weekly_total(self) -> int:
        return self._weekly.get("input", 0) + self._weekly.get("output", 0)

    def fmt(self, n: int) -> str:
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M"
        return f"{n / 1000:.1f}k" if n >= 1000 else str(n)

    def _pct(self, tokens: int, limit: int) -> str:
        if limit <= 0:
            return ""
        pct = min(tokens / limit * 100, 100)
        return f" ({pct:.0f}%)"

    def toolbar_text(self) -> str:
        if self.session_total == 0 and self.weekly_total == 0:
            return ""
        parts = []
        limit = _WEEKLY_LIMIT
        if self.session_total > 0:
            parts.append(
                f"session: {self.fmt(self.session_total)} tok"
                f"  ({self.fmt(self.session_input)} in / {self.fmt(self.session_output)} out)"
            )
        parts.append(
            f"weekly: {self.fmt(self.weekly_total)} tok{self._pct(self.weekly_total, limit)}"
        )
        return "  │  ".join(parts)


# ── Auto-router classifier ─────────────────────────────────────────────

_CLASSIFY_PROMPT = (
    "Classify the following user message into exactly ONE category.\n"
    "Reply with ONLY the category name, nothing else.\n\n"
    "Categories:\n"
    "  code     — write new code, refactor, implement features\n"
    "  debug    — fix bugs, analyze errors, troubleshoot\n"
    "  review   — review code, suggest improvements, analyze quality\n"
    "  docs     — write documentation, explain code, tutorials\n"
    "  general  — general questions, conversation, anything else\n\n"
    "User message:\n"
)

# Default auto-routing: category → (provider, model)
# Prefers cloud models for performance on weaker PCs
_AUTO_ROUTES: dict[str, tuple[str, str]] = {
    "code":    ("openrouter", "anthropic/claude-3.5-sonnet"),
    "debug":   ("openrouter", "anthropic/claude-3.5-sonnet"),
    "review":  ("openrouter", "anthropic/claude-3.5-sonnet"),
    "docs":    ("openrouter", "anthropic/claude-3.5-sonnet"),
    "general": ("openrouter", "anthropic/claude-3.5-sonnet"),
}


def _is_ollama_model_available(model: str) -> bool:
    """Check if a model is available locally in Ollama."""
    try:
        out = subprocess.check_output(
            ["ollama", "list"], text=True, timeout=5, stderr=subprocess.DEVNULL,
        )
        installed = {line.split()[0] for line in out.strip().splitlines()[1:] if line.strip()}
        return model in installed
    except Exception:
        return False


def _pull_ollama_model(model: str) -> bool:
    """Pull an Ollama model. Returns True if successful."""
    try:
        console.print(f"[dim]Downloading [bold]{model}[/bold]... (this may take a while)[/dim]")
        subprocess.run(
            ["ollama", "pull", model],
            check=True, timeout=600,
        )
        console.print(f"[green]✓[/green] Model [bold]{model}[/bold] downloaded")
        return True
    except Exception as e:
        console.print(f"[red]Error downloading model:[/red] {e}")
        return False


# Tools that only read data — never need user consent
_SAFE_TOOLS = {"read_file", "list_dir", "grep", "find_files", "search_knowledge", "web_search", "web_fetch"}

# Bash commands that are particularly destructive
_DANGEROUS_COMMANDS = {"rm", "rmdir", "del", "format", "mkfs", "dd", "shred", ">"}


class Agent:
    def __init__(self, config: Config):
        self.config = config
        self.base_config = config  # original config, used as fallback
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
        )
        self.messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": _build_context_block()},
        ]
        self.usage = Usage()
        self.auto_approve = False  # toggle with /auto
        self.quiet_mode = load_quiet_pref()
        self.rag_mode = load_rag_mode()
        self.routing_mode = load_routing_mode()
        self.static_rules = load_static_rules()
        self.web_enabled = load_web_enabled()
        self.web_provider = load_web_provider()
        self.retriever = Retriever(
            embed_model=os.getenv("OLLAMA_EMBED_MODEL") or None
        )
        self.mcp = MCPManager()
        # Start MCP in the background — any failure is recorded in mcp.errors
        # and does not break the rest of ola.
        try:
            self.mcp.start()
        except Exception:
            pass

    def _system_prefix_count(self) -> int:
        """Count contiguous system messages at the start (system prompt + context + optional RAG hint)."""
        n = 0
        for msg in self.messages:
            if msg.get("role") == "system":
                n += 1
            else:
                break
        return n

    def _transcript_for_summary(self, messages: list[dict]) -> str:
        """Render a compact text transcript of non-system messages for summarization."""
        lines: list[str] = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if isinstance(content, list):
                # Multimodal content: keep only the text parts
                content = " ".join(
                    (part.get("text", "") if isinstance(part, dict) else str(part))
                    for part in content
                )
            if role == "tool":
                text = str(content or "").strip()
                if len(text) > 400:
                    text = text[:400] + " …[truncated]"
                lines.append(f"[tool result] {text}")
            elif role == "assistant":
                text = str(content or "").strip()
                tool_calls = msg.get("tool_calls") or []
                if tool_calls:
                    names = ", ".join(tc.get("function", {}).get("name", "?") for tc in tool_calls)
                    prefix = f"[assistant called: {names}] "
                else:
                    prefix = "[assistant] "
                if text:
                    lines.append(prefix + text)
                elif tool_calls:
                    lines.append(prefix.strip())
            elif role == "user":
                lines.append(f"[user] {str(content or '').strip()}")
        return "\n".join(lines)

    def compact(self) -> tuple[int, int, int]:
        """Summarize the non-system conversation history into a single system message.

        Returns (messages_before, messages_after, summary_chars).
        Raises on LLM errors so the caller can inform the user.
        """
        prefix = self._system_prefix_count()
        tail = self.messages[prefix:]
        before = len(self.messages)

        if not tail:
            return (before, before, 0)

        transcript = self._transcript_for_summary(tail)
        if not transcript.strip():
            return (before, before, 0)

        prompt = (
            "You are compressing a coding assistant's conversation history to save tokens.\n"
            "Produce a concise summary of the exchange so far, capturing:\n"
            "  • the user's goals and constraints,\n"
            "  • key decisions and outcomes,\n"
            "  • files created/modified and their purpose,\n"
            "  • open tasks or known issues.\n"
            "Be terse — bullet points, no pleasantries. Stay under ~350 words.\n\n"
            "--- Conversation transcript ---\n"
            + transcript
            + "\n--- End ---\n\nSummary:"
        )

        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[{"role": "system", "content": prompt}],
            temperature=0.2,
            max_tokens=600,
        )
        summary = (response.choices[0].message.content or "").strip()
        if not summary:
            return (before, before, 0)

        self.messages = self.messages[:prefix] + [
            {
                "role": "system",
                "content": "Summary of prior conversation (compacted to save context):\n" + summary,
            }
        ]
        return (before, len(self.messages), len(summary))

    def propose_commit_message(self, status: str, diff: str, recent_log: str) -> str:
        """Ask the current LLM to propose a commit message based on staged/unstaged changes."""
        # Trim very large diffs so we don't blow the context
        if len(diff) > 8000:
            diff = diff[:8000] + "\n…[diff truncated]"
        prompt = (
            "You are helping the user write a git commit message for their staged changes.\n"
            "Match the tone and formatting of the recent log (imperative, same language if clear).\n"
            "Output ONLY the commit message — no fences, no preface, no explanation.\n"
            "Keep the subject line ≤72 characters. Add a body only if meaningful.\n\n"
            f"Recent log:\n{recent_log.strip() or '(no prior commits)'}\n\n"
            f"git status:\n{status.strip() or '(empty)'}\n\n"
            f"Changes:\n{diff.strip() or '(no diff)'}\n"
        )
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[{"role": "system", "content": prompt}],
            temperature=0.2,
            max_tokens=300,
        )
        return (response.choices[0].message.content or "").strip()

    def refresh_context(self) -> None:
        self.messages[1] = {"role": "system", "content": _build_context_block()}
        # Keep the RAG-mode hint in sync with the current preference.
        mode_hint = (
            "RAG mode: RLM (recursive). Prefer the 'deep_query' tool over "
            "'search_knowledge' for knowledge-base questions — it scans ALL chunks "
            "of the relevant files via recursive LLM calls, preserving global context."
            if self.rag_mode == "rlm"
            else "RAG mode: standard (top-k). Use 'search_knowledge' for knowledge-base "
                 "questions — it is fast and returns the most relevant chunks."
        )
        if len(self.messages) >= 3 and self.messages[2].get("role") == "system" and self.messages[2].get("content", "").startswith("RAG mode:"):
            self.messages[2] = {"role": "system", "content": mode_hint}
        else:
            self.messages.insert(2, {"role": "system", "content": mode_hint})

    # ── Model routing ──────────────────────────────────────────────────

    def _classify_message(self, message: str) -> str:
        """Use a lightweight model to classify the user message into a task category."""
        try:
            # Use current client (could be cloud) for classification — fast & cheap
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": _CLASSIFY_PROMPT + message},
                ],
                max_tokens=10,
                temperature=0,
            )
            category = response.choices[0].message.content.strip().lower()
            # Normalize: accept partial matches
            for cat in TASK_CATEGORIES:
                if cat in category:
                    return cat
            return "general"
        except Exception:
            return "general"

    def _ensure_model_available(self, provider: str, model: str) -> bool:
        """Ensure the model is available. For Ollama, prompt to download if missing."""
        if provider != "ollama":
            return True
        if _is_ollama_model_available(model):
            return True
        # Ask user before downloading
        console.print(f"[yellow]Model [bold]{model}[/bold] is not installed locally.[/yellow]")
        try:
            answer = input(f"  Download it? (may use several GB of disk) [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return False
        if answer not in ("y", "yes", "si", "sì", "s"):
            return False
        return _pull_ollama_model(model)

    def _apply_routing(self, message: str) -> str | None:
        """Select model based on routing mode. Returns the chosen category or None."""
        if self.routing_mode == "manual":
            return None

        if self.routing_mode == "auto":
            spinner = console.status("[dim]classifying request...[/dim]", spinner="dots")
            spinner.start()
            category = self._classify_message(message)
            spinner.stop()

            route = _AUTO_ROUTES.get(category, _AUTO_ROUTES["general"])
            provider, model = route

            if not self._ensure_model_available(provider, model):
                console.print(f"[dim]Fallback to current model: {self.config.model}[/dim]")
                return category

            self._switch_client(provider, model)
            console.print(f"[dim]  routing: [bold]{category}[/bold] → {provider}/{model}[/dim]")
            return category

        if self.routing_mode == "static":
            # Simple keyword-based classification for static mode
            category = self._classify_static(message)
            model = self.static_rules.get(category, self.static_rules.get("general", self.config.model))

            # Determine provider from model name
            provider = self._detect_provider(model)

            if not self._ensure_model_available(provider, model):
                console.print(f"[dim]Fallback to current model: {self.config.model}[/dim]")
                return category

            self._switch_client(provider, model)
            console.print(f"[dim]  routing: [bold]{category}[/bold] → {provider}/{model}[/dim]")
            return category

        return None

    def _classify_static(self, message: str) -> str:
        """Simple keyword-based classification for static routing."""
        msg = message.lower()
        code_words = {"scrivi", "crea", "implementa", "genera", "codice", "funzione",
                      "classe", "write", "create", "implement", "function", "class",
                      "refactor", "component", "method", "metodo"}
        debug_words = {"bug", "errore", "error", "fix", "debug", "crash", "broken",
                       "rotto", "non funziona", "doesn't work", "traceback", "exception"}
        review_words = {"review", "analizza", "controlla", "check", "valuta", "migliora",
                        "improve", "quality", "ottimizza", "optimize"}
        docs_words = {"spiega", "explain", "documenta", "document", "readme", "commenta",
                      "comment", "tutorial", "guida", "guide", "come funziona", "how does"}

        words = set(msg.split())
        if words & debug_words or any(w in msg for w in ("non funziona", "doesn't work")):
            return "debug"
        if words & review_words:
            return "review"
        if words & docs_words or any(w in msg for w in ("come funziona", "how does")):
            return "docs"
        if words & code_words:
            return "code"
        return "general"

    def _detect_provider(self, model: str) -> str:
        """Detect provider from model name."""
        if "/" in model:
            # Looks like openrouter format (e.g. anthropic/claude-3.5-sonnet)
            return "openrouter"
        if model.startswith("gpt-"):
            return "openai"
        # Default to ollama for local models
        return "ollama"

    def _switch_client(self, provider: str, model: str) -> None:
        """Temporarily switch the OpenAI client to a different provider/model."""
        if provider == self.config.provider and model == self.config.model:
            return

        pconf = PROVIDERS.get(provider)
        if not pconf:
            return

        api_key = os.getenv(pconf["env_key"], "ollama" if provider == "ollama" else "")
        if not api_key and provider != "ollama":
            console.print(f"[yellow]No API key for {provider}, staying on current model[/yellow]")
            return

        self.client = OpenAI(api_key=api_key, base_url=pconf["base_url"])
        self.config = Config(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=pconf["base_url"],
        )

    def _restore_client(self) -> None:
        """Restore the client to the base config after a routed call."""
        if self.config != self.base_config:
            self.config = self.base_config
            self.client = OpenAI(
                api_key=self.base_config.api_key,
                base_url=self.base_config.base_url,
            )

    # ── Image attachment support ───────────────────────────────────────

    _IMG_EXTS = ("png", "jpg", "jpeg", "gif", "webp", "bmp")

    def _extract_images(self, text: str) -> tuple[str, list[str]]:
        """Find image file paths in the user message.

        Supports quoted paths (with spaces) and unquoted tokens. Returns the
        cleaned text (with paths removed) and the list of resolved image paths.
        """
        exts = "|".join(self._IMG_EXTS)
        pattern = (
            rf'"([^"]+\.(?:{exts}))"'   # "path with spaces.png"
            rf"|'([^']+\.(?:{exts}))'"  # 'path with spaces.png'
            rf"|(\S+\.(?:{exts}))"       # /unquoted/path.png
        )

        found: list[str] = []

        def replace(match: re.Match) -> str:
            raw = match.group(1) or match.group(2) or match.group(3)
            p = Path(os.path.expanduser(raw))
            if p.exists() and p.is_file():
                found.append(str(p.resolve()))
                return ""
            return match.group(0)

        cleaned = re.sub(pattern, replace, text, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", cleaned).strip(), found

    def _encode_image(self, path: str) -> str | None:
        """Encode an image file as a base64 data URL. Returns None on failure."""
        try:
            mime, _ = mimetypes.guess_type(path)
            if not mime or not mime.startswith("image/"):
                return None
            with open(path, "rb") as f:
                data = base64.b64encode(f.read()).decode("ascii")
            return f"data:{mime};base64,{data}"
        except Exception:
            return None

    def chat(self, user_message: str) -> None:
        self.refresh_context()

        # Detect image paths in the user message and build multimodal content
        text, image_paths = self._extract_images(user_message)

        if image_paths:
            content: list[dict] = []
            content.append({"type": "text", "text": text or "Describe this image."})
            for img in image_paths:
                data_url = self._encode_image(img)
                if data_url is None:
                    console.print(f"[yellow]  ⚠ could not read image: {Path(img).name}[/yellow]")
                    continue
                content.append({
                    "type": "image_url",
                    "image_url": {"url": data_url},
                })
                console.print(f"[dim]  📎 attached: {Path(img).name}[/dim]")
            self.messages.append({"role": "user", "content": content})
        else:
            self.messages.append({"role": "user", "content": user_message})

        # Apply routing if not manual (classify on the text portion only)
        routed = self._apply_routing(text or user_message)

        while True:
            response_text, tool_calls = self._stream_response()

            if tool_calls:
                self.messages.append({
                    "role": "assistant",
                    "content": response_text or None,
                    "tool_calls": tool_calls,
                })

                for tc in tool_calls:
                    name = tc["function"]["name"]
                    try:
                        args = json.loads(tc["function"]["arguments"])
                    except json.JSONDecodeError:
                        args = {}

                    self._show_tool_call(name, args)

                    # Block access to knowledge base source files
                    blocked = self._guard_kb_access(name, args)
                    if blocked:
                        console.print(f"  [yellow]✗[/yellow] [dim]{blocked}[/dim]")
                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": blocked,
                        })
                        continue

                    # Ask for consent on write/execute operations
                    if not self._check_consent(name, args):
                        result = "Tool execution denied by user."
                        console.print(f"  [yellow]✗[/yellow] [dim]{result}[/dim]")
                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": result,
                        })
                        continue

                    # Spinner during tool execution
                    spinner = console.status(
                        f"[dim]running {name}...[/dim]", spinner="dots"
                    )
                    spinner.start()
                    try:
                        if self.mcp.is_mcp_tool(name):
                            result = self.mcp.call_tool(name, args)
                        else:
                            result = execute_tool(
                                name, args,
                                retriever=self.retriever,
                                llm_client=self.client,
                                llm_model=self.config.model,
                                web_provider=self.web_provider,
                            )
                    finally:
                        spinner.stop()

                    self._show_tool_result(result)
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    })
                continue

            else:
                if response_text:
                    self.messages.append({"role": "assistant", "content": response_text})
                break

        # Restore original model after routed call
        if routed:
            self._restore_client()

    def _stream_response(self) -> tuple[str, list[dict]]:
        """Stream the model response. Returns (text, tool_calls)."""
        response_text = ""
        tool_calls_raw: dict[int, dict] = {}

        # Spinner shown until the first token or tool call arrives
        spinner = console.status("[dim]thinking...[/dim]", spinner="dots")
        spinner.start()
        spinner_stopped = False
        thinking_tokens = 0  # track <think> tokens for Qwen3-style models

        def stop_spinner() -> None:
            nonlocal spinner_stopped
            if not spinner_stopped:
                spinner.stop()
                spinner_stopped = True

        def update_spinner(text: str) -> None:
            if not spinner_stopped:
                spinner.update(f"[dim]{text}[/dim]")

        try:
            # Try with include_usage; some local models don't support it
            try:
                all_tools = TOOL_DEFINITIONS + (self.mcp.tools if self.mcp else [])
                if self.web_enabled:
                    all_tools = all_tools + WEB_TOOL_DEFINITIONS
                stream = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=self.messages,
                    tools=all_tools,
                    tool_choice="auto",
                    stream=True,
                    stream_options={"include_usage": True},
                )
                # Consume one chunk to verify the stream works
                first = next(iter(stream), None)
                chunks = ([first] if first else [])
                chunks_iter = (c for c in [*chunks, *stream])
            except Exception:
                # Retry without stream_options
                stream = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=self.messages,
                    tools=all_tools,
                    tool_choice="auto",
                    stream=True,
                )
                chunks_iter = iter(stream)

            in_think_block = False

            for chunk in chunks_iter:
                if not chunk.choices:
                    if hasattr(chunk, "usage") and chunk.usage:
                        self.usage.update(
                            chunk.usage.prompt_tokens,
                            chunk.usage.completion_tokens,
                            provider=self.config.provider,
                            model=self.config.model,
                        )
                    continue

                delta = chunk.choices[0].delta

                if delta.content:
                    text = delta.content

                    # Handle Qwen3-style <think>...</think> blocks
                    if "<think>" in text:
                        in_think_block = True
                    if in_think_block:
                        thinking_tokens += len(text.split())
                        update_spinner(f"reasoning... ({thinking_tokens} tok)")
                        if "</think>" in text:
                            in_think_block = False
                            update_spinner("thinking...")
                        continue  # don't print thinking tokens

                    stop_spinner()
                    print(text, end="", flush=True)
                    response_text += text

                if delta.tool_calls:
                    stop_spinner()
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_raw:
                            tool_calls_raw[idx] = {
                                "id": "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            }
                        if tc.id:
                            tool_calls_raw[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tool_calls_raw[idx]["function"]["name"] += tc.function.name
                            if tc.function.arguments:
                                tool_calls_raw[idx]["function"]["arguments"] += tc.function.arguments

            stop_spinner()
            if response_text:
                print()

        except KeyboardInterrupt:
            stop_spinner()
            print()
            raise
        except Exception as e:
            stop_spinner()
            console.print(f"\n[red]Error: {e}[/red]")
            return "", []

        tool_calls = [tool_calls_raw[i] for i in sorted(tool_calls_raw)]
        return response_text, tool_calls

    def _show_tool_call(self, name: str, args: dict) -> None:
        if self.quiet_mode:
            console.print(f"[dim]  · {name}[/dim]")
            return
        parts = []
        for k, v in args.items():
            v_str = repr(v)
            if len(v_str) > 60:
                v_str = v_str[:57] + "..."
            parts.append(f"{k}={v_str}")
        console.print(f"\n[bold cyan]  {name}[/bold cyan]([dim]{', '.join(parts)}[/dim])")

    def _show_tool_result(self, result: str) -> None:
        if self.quiet_mode:
            return
        lines = result.strip().splitlines()
        preview = "\n    ".join(lines[:4])
        suffix = f"\n    [dim]... ({len(lines) - 4} more lines)[/dim]" if len(lines) > 4 else ""
        console.print(f"  [green]✓[/green] [dim]  {preview}{suffix}[/dim]")

    # ── Consent system ──────────────────────────────────────────────────────

    # ── Knowledge base file guard ────────────────────────────────────────

    def _guard_kb_access(self, name: str, args: dict) -> str | None:
        """Block attempts to read knowledge base source files.

        Returns an error message if blocked, None if allowed.
        """
        kb_sources = set(self.retriever.sources)
        if not kb_sources:
            return None

        # read_file — direct path check
        if name == "read_file":
            path = str(Path(args.get("path", "")).resolve())
            if path in kb_sources:
                return (
                    f"BLOCKED: '{Path(path).name}' is in the knowledge base. "
                    "Use search_knowledge to query its content instead of reading the file directly."
                )

        # bash — check if command references a KB file
        if name == "bash":
            cmd = args.get("command", "")
            # Common read commands that should not target KB files
            read_cmds = ("cat ", "head ", "tail ", "less ", "more ", "strings ", "xxd ", "hexdump ")
            if any(cmd.strip().startswith(rc) for rc in read_cmds):
                for src in kb_sources:
                    if src in cmd or Path(src).name in cmd:
                        return (
                            f"BLOCKED: '{Path(src).name}' is in the knowledge base. "
                            "Use search_knowledge to query its content instead of reading the file directly."
                        )

        return None

    def _check_consent(self, name: str, args: dict) -> bool:
        """Return True if the tool execution is approved."""
        if self.auto_approve or name in _SAFE_TOOLS:
            return True

        # Show preview for edit operations
        if name == "edit_file":
            self._show_diff(args)

        # Show preview for write operations (new file content)
        elif name == "write_file":
            self._show_write_preview(args)

        # Highlight dangerous bash commands
        elif name == "bash":
            cmd = args.get("command", "")
            first_word = cmd.strip().split()[0] if cmd.strip() else ""
            if first_word in _DANGEROUS_COMMANDS or "rm " in cmd or "rm -" in cmd:
                console.print(f"  [bold red]⚠ Destructive command detected[/bold red]")

        return self._ask_user()

    def _ask_user(self) -> bool:
        """Prompt the user for approval. Returns True if approved."""
        try:
            answer = input("  Execute? [Y/n/auto] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return False
        if answer in ("auto", "a"):
            self.auto_approve = True
            console.print("  [dim]Auto-approve enabled for this session. Use /manual to disable.[/dim]")
            return True
        return answer not in ("n", "no")

    def _show_diff(self, args: dict) -> None:
        """Show a colored diff preview for edit_file operations."""
        path = args.get("path", "")
        old = args.get("old_string", "")
        new = args.get("new_string", "")

        if not old and not new:
            return

        diff = Text()
        diff.append(f"  {path}\n", style="bold")

        old_lines = old.splitlines()
        new_lines = new.splitlines()

        for line in old_lines:
            diff.append(f"  - {line}\n", style="red")
        for line in new_lines:
            diff.append(f"  + {line}\n", style="green")

        console.print(Panel(
            diff,
            title="[bold]Diff preview[/bold]",
            border_style="dim",
            padding=(0, 1),
        ))

    def _show_write_preview(self, args: dict) -> None:
        """Show a preview for write_file operations."""
        path = args.get("path", "")
        content = args.get("content", "")

        p = Path(path)
        is_new = not p.exists()
        lines = content.splitlines()

        preview = Text()
        preview.append(f"  {path}", style="bold")
        if is_new:
            preview.append("  (new file)", style="yellow")
        else:
            preview.append("  (overwrite)", style="red")
        preview.append("\n")

        # Show first 10 lines of content
        show_lines = lines[:10]
        for line in show_lines:
            style = "green" if is_new else "yellow"
            prefix = "+" if is_new else "~"
            preview.append(f"  {prefix} {line}\n", style=style)
        if len(lines) > 10:
            preview.append(f"  ... ({len(lines) - 10} more lines)\n", style="dim")

        console.print(Panel(
            preview,
            title="[bold]Write preview[/bold]",
            border_style="dim",
            padding=(0, 1),
        ))
