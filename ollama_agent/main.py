import os
import subprocess
import sys
from pathlib import Path

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .agent import Agent
from .config import (
    PROVIDERS, Config, save_user_prefs,
    ROUTING_MODES, TASK_CATEGORIES, RAG_MODES,
    save_routing_mode, load_static_rules, save_static_rules,
    save_auto_save_pref, load_auto_save_pref,
    save_quiet_pref, load_quiet_pref,
    save_rag_mode,
    save_language, load_language, LANGUAGES,
    save_web_enabled, load_web_enabled,
    save_web_provider, load_web_provider, WEB_PROVIDERS,
)
from .sessions import save_session, list_sessions, load_session
from .backups import undo_last, stack_size
from .costs import estimate_cost, lookup_price, fmt_usd

console = Console()

BANNER = (
    "   [bold cyan]┌────────┐[/bold cyan]\n"
    "   [bold cyan]│[/bold cyan] [cyan]◉[/cyan]    [cyan]◉[/cyan] [bold cyan]│[/bold cyan]   ⚡ [bold cyan]Ollama Agent[/bold cyan]  [dim]v0.8.0 — AI coding assistant[/dim]\n"
    "   [bold cyan]│  ────  │[/bold cyan]   [dim]────────────────────────────────────[/dim]\n"
    "   [bold cyan]└───┬────┘[/bold cyan]   Type [bold]/[/bold] for commands\n"
    "  [bold cyan]┌────┴─────┐[/bold cyan]  [bold]Ctrl+C[/bold] cancel  ·  [bold]Ctrl+D[/bold] exit\n"
    "  [bold cyan]│  O·L·A   │[/bold cyan]\n"
    "  [bold cyan]└──────────┘[/bold cyan]"
)

# Each entry: (command, argument_hint, description_en, description_it)
_COMMANDS_BILINGUAL = [
    ("/help",      "",
        "Show available commands",
        "Mostra i comandi disponibili"),
    ("/clear",     "",
        "Clear conversation history",
        "Pulisce la cronologia della conversazione"),
    ("/init",      "",
        "Create AGENT.md project context file",
        "Crea il file AGENT.md per il contesto progetto"),
    ("/learn",     "<path> [--force]",
        "Index a file or directory (use --force to re-index)",
        "Indicizza un file o una cartella (con --force forza la reindicizzazione)"),
    ("/ask",       "<file> <question>",
        "Ask a question scoped to a single indexed file",
        "Domanda ristretta a un singolo file indicizzato"),
    ("/voice",     "",
        "Dictate your prompt via microphone (Enter to stop)",
        "Detta il prompt dal microfono (Invio per terminare)"),
    ("/knowledge", "",
        "Show what is indexed in the knowledge base",
        "Mostra cosa è indicizzato nella knowledge base"),
    ("/model",     "<name>",
        "Show or switch the active model",
        "Mostra o cambia il modello attivo"),
    ("/models",    "",
        "List models available in Ollama",
        "Elenca i modelli disponibili in Ollama"),
    ("/provider",  "<name>",
        "Switch provider (ollama/openai/groq/openrouter)",
        "Cambia provider (ollama/openai/groq/openrouter)"),
    ("/settings",  "",
        "Show current configuration",
        "Mostra la configurazione corrente"),
    ("/tools",     "",
        "List available tools",
        "Elenca gli strumenti disponibili"),
    ("/routing",   "<mode>",
        "Switch routing mode (manual/auto/static)",
        "Cambia modalità di routing (manual/auto/static)"),
    ("/ragmode",   "<mode>",
        "Switch RAG retrieval mode (standard/rlm)",
        "Cambia modalità RAG (standard/rlm)"),
    ("/rules",     "[args]",
        "Manage static routing rules (list/set/reset)",
        "Gestisce le regole di routing statico (list/set/reset)"),
    ("/save",      "[title]",
        "Save current session",
        "Salva la sessione corrente"),
    ("/sessions",  "",
        "List saved sessions",
        "Elenca le sessioni salvate"),
    ("/resume",    "[#]",
        "Resume a saved session (default: most recent)",
        "Riprende una sessione salvata (default: la più recente)"),
    ("/autosave",  "",
        "Toggle auto-save on exit",
        "Attiva/disattiva il salvataggio automatico all'uscita"),
    ("/mcp",       "<subcmd>",
        "Manage MCP servers (list/tools/enable/disable/add/remove/reload)",
        "Gestione server MCP (list/tools/enable/disable/add/remove/reload)"),
    ("/web",       "[on|off|provider <name>]",
        "Toggle web search or switch provider (duckduckgo/brave/tavily)",
        "Attiva/disattiva ricerca web o cambia provider (duckduckgo/brave/tavily)"),
    ("/compact",   "",
        "Summarize conversation to save context tokens",
        "Riassume la conversazione per risparmiare token di contesto"),
    ("/commit",    "",
        "Generate a commit message for staged changes and commit",
        "Genera un messaggio di commit per le modifiche staged e committa"),
    ("/undo",      "",
        "Undo the last file edit performed by the agent",
        "Annulla l'ultima modifica di file fatta dall'agent"),
    ("/costs",     "",
        "Show estimated session and weekly costs per provider/model",
        "Mostra costi stimati di sessione e settimana per provider/modello"),
    ("/quiet",     "",
        "Toggle quiet mode (hide tool call details)",
        "Attiva/disattiva la modalità silenziosa"),
    ("/lang",      "<it|en>",
        "Switch interface language",
        "Cambia lingua dell'interfaccia"),
    ("/auto",      "",
        "Auto-approve all tool executions",
        "Approva automaticamente tutte le operazioni"),
    ("/manual",    "",
        "Ask consent before write/execute operations (default)",
        "Chiede consenso prima delle operazioni di scrittura/esecuzione"),
    ("/exit",      "",
        "Exit Ollama Code",
        "Esci da ola"),
]


def _commands(lang: str = "it") -> list[tuple[str, str, str]]:
    """Return (cmd, hint, description) tuples in the requested language."""
    idx = 3 if lang == "it" else 2
    return [(e[0], e[1], e[idx]) for e in _COMMANDS_BILINGUAL]


# Legacy alias kept for completer/help which read COMMANDS directly.
# Rebound at startup based on saved language preference.
COMMANDS = _commands(load_language())

PROMPT_STYLE = Style.from_dict({"prompt": "bold cyan"})


class SlashCompleter(Completer):
    """Show command completions when the line starts with '/'."""

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if not text.startswith("/"):
            return

        word = text.lstrip("/").lower()
        for cmd, hint, desc in _commands(load_language()):
            name = cmd.lstrip("/")
            if name.startswith(word):
                safe_hint = hint.replace("<", "&lt;").replace(">", "&gt;")
                display = HTML(
                    f"<b>{cmd}</b>"
                    + (f" <ansigray>{safe_hint}</ansigray>" if hint else "")
                )
                yield Completion(
                    cmd,
                    start_position=-len(text),
                    display=display,
                    display_meta=desc,
                )


def _list_ollama_models() -> list[str]:
    try:
        out = subprocess.check_output(["ollama", "list"], text=True, timeout=5)
        lines = out.strip().splitlines()[1:]  # skip header
        return [line.split()[0] for line in lines if line.strip()]
    except Exception:
        return []


def _show_settings(agent: Agent) -> None:
    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column(style="dim")
    t.add_column(style="bold")
    t.add_row("provider", agent.config.provider)
    t.add_row("model", agent.config.model)
    t.add_row("base_url", agent.config.base_url)
    t.add_row("routing", agent.routing_mode)
    t.add_row("rag mode", agent.rag_mode)
    t.add_row("approve", "auto" if agent.auto_approve else "manual (ask consent)")
    t.add_row("auto-save", "on" if load_auto_save_pref() else "off")
    t.add_row("quiet mode", "on" if agent.quiet_mode else "off")
    web_state = f"on ({agent.web_provider})" if agent.web_enabled else "off"
    t.add_row("web access", web_state)
    t.add_row("language", load_language())
    t.add_row("messages", str(len(agent.messages) - 1))  # exclude system prompt
    console.print(Panel(t, title="[bold]Settings[/bold]", border_style="cyan", padding=(0, 1)))


def _show_rules(agent: Agent) -> None:
    t = Table(show_header=True, box=None, padding=(0, 2))
    t.add_column("Category", style="bold cyan", no_wrap=True)
    t.add_column("Model", style="bold")
    for cat in TASK_CATEGORIES:
        model = agent.static_rules.get(cat, "—")
        t.add_row(cat, model)
    console.print(Panel(t, title="[bold]Static routing rules[/bold]", border_style="cyan", padding=(0, 1)))
    console.print("[dim]  Change with: /rules <category>=<model>  (e.g. /rules code=deepseek-coder-v2)[/dim]")


def _show_help() -> None:
    lang = load_language()
    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column(style="bold cyan", no_wrap=True)
    t.add_column(style="dim", no_wrap=True)
    t.add_column()
    for cmd, hint, desc in _commands(lang):
        t.add_row(cmd, hint, desc)
    title = "Comandi" if lang == "it" else "Commands"
    hint_line = (
        "  Tastiera: Ctrl+C annulla risposta · Ctrl+D esce · ↑↓ cronologia"
        if lang == "it"
        else "  Keyboard: Ctrl+C cancel response · Ctrl+D exit · ↑↓ history"
    )
    console.print(Panel(t, title=f"[bold]{title}[/bold]", border_style="cyan", padding=(0, 1)))
    console.print(f"[dim]{hint_line}[/dim]")


def _show_tools() -> None:
    tools = [
        ("bash",       "Execute shell commands"),
        ("read_file",  "Read a file with line numbers"),
        ("write_file", "Create or overwrite a file"),
        ("edit_file",  "Replace an exact string in a file"),
        ("list_dir",   "List directory contents"),
        ("grep",       "Search files with regex"),
        ("find_files", "Find files by glob pattern"),
        ("web_search", "Search the web (enable with /web on)"),
        ("web_fetch",  "Fetch a URL and read its content (enable with /web on)"),
    ]
    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column(style="bold cyan", no_wrap=True)
    t.add_column()
    for name, desc in tools:
        t.add_row(name, desc)
    console.print(Panel(t, title="[bold]Tools[/bold]", border_style="cyan", padding=(0, 1)))


def _cmd_learn(agent: Agent, path: str, force: bool = False) -> None:
    """Index a file or directory into the knowledge base."""
    import time
    from pathlib import Path as _Path
    from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn, MofNCompleteColumn, SpinnerColumn

    target = _Path(path)
    if not target.exists():
        console.print(f"[red]Path not found:[/red] {path}")
        return

    parallel = int(os.getenv("OLLAMA_AGENT_EMBED_PARALLEL", "4"))

    # Warn if the KB was built with a different model — will auto-clear on index
    if agent.retriever._model_mismatch:
        console.print(
            f"[yellow]Embedding model changed:[/yellow] "
            f"[dim]{agent.retriever._model_mismatch}[/dim] → [bold]{agent.retriever.embed_model}[/bold]\n"
            f"[yellow]The knowledge base will be re-indexed with the new model.[/yellow]"
        )
        force = True

    mode = "[yellow]force re-index[/yellow]" if force else "incremental"
    console.print(
        f"[dim]Indexing [bold]{path}[/bold] with model [bold]{agent.retriever.embed_model}[/bold] "
        f"({mode}, [bold]{parallel}[/bold] parallel workers)[/dim]"
    )

    # Phase 1: scanning — show spinner while building file list
    scan_status = console.status("[dim]Scanning directory...[/dim]", spinner="dots")
    scan_status.start()

    need_embed = False

    def on_scan(total_on_disk: int, new_count: int, modified_count: int) -> None:
        nonlocal need_embed
        scan_status.stop()
        skipped = total_on_disk - new_count - modified_count
        parts = []
        if new_count:
            parts.append(f"[green]{new_count} new[/green]")
        if modified_count:
            parts.append(f"[yellow]{modified_count} modified[/yellow]")
        if skipped:
            parts.append(f"[dim]{skipped} unchanged[/dim]")
        summary = ", ".join(parts) if parts else "0 files"
        console.print(f"[dim]  Found [bold]{total_on_disk}[/bold] file(s): {summary}[/dim]")
        need_embed = (new_count + modified_count) > 0
        if need_embed:
            console.print(f"[dim]  Chunking files and warming up embed model...[/dim]")

    # Phase 2: embedding — progress bar with ETA, granular at the chunk level
    progress_bar: Progress | None = None
    task_id = None

    def progress(
        filename: str,
        chunks_done_total: int,
        chunks_total: int,
        in_file_done: int,
        in_file_total: int,
    ) -> None:
        nonlocal progress_bar, task_id
        if progress_bar is None:
            progress_bar = Progress(
                SpinnerColumn("dots"),
                TextColumn("[dim]{task.description}[/dim]"),
                BarColumn(bar_width=30),
                MofNCompleteColumn(),
                TextColumn("[cyan]{task.percentage:>5.1f}%[/cyan]"),
                TimeElapsedColumn(),
                TextColumn("ETA"),
                TimeRemainingColumn(),
                console=console,
            )
            task_id = progress_bar.add_task("Indexing", total=max(chunks_total, 1))
            progress_bar.start()
        # Truncate very long filenames so the line stays readable
        short = filename if len(filename) <= 48 else filename[:45] + "..."
        desc = f"↳ {short} [{in_file_done}/{in_file_total}]"
        progress_bar.update(task_id, completed=chunks_done_total, description=desc)

    t0 = time.monotonic()
    try:
        files, chunks = agent.retriever.index(
            path, progress_cb=progress, scan_cb=on_scan, force=force
        )
    except KeyboardInterrupt:
        if progress_bar is not None:
            progress_bar.stop()
        console.print("\n[yellow]Interrupted.[/yellow] Per-file progress was saved.")
        console.print(f"[dim]  Knowledge base: {agent.retriever.source_count} sources, {agent.retriever.chunk_count} chunks total[/dim]")
        return
    except Exception as e:
        scan_status.stop()
        if progress_bar is not None:
            progress_bar.stop()
        console.print(f"\n[red]Error:[/red] {e}")
        console.print(f"[dim]Make sure the embed model is pulled: [bold]ollama pull {agent.retriever.embed_model}[/bold][/dim]")
        return

    if progress_bar is not None:
        progress_bar.stop()

    elapsed = time.monotonic() - t0
    if elapsed >= 60:
        elapsed_str = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"
    else:
        elapsed_str = f"{elapsed:.1f}s"

    if files > 0:
        console.print(
            f"[green]✓[/green] Indexed [bold]{files}[/bold] file(s) → "
            f"[bold]{chunks}[/bold] chunks in [bold]{elapsed_str}[/bold]"
        )
    else:
        console.print(f"[green]✓[/green] Knowledge base already up to date — nothing to re-index")
    console.print(f"[dim]  Knowledge base: {agent.retriever.source_count} sources, {agent.retriever.chunk_count} chunks total[/dim]")


def _cmd_knowledge(agent: Agent) -> None:
    """Show what is indexed in the knowledge base, grouped by folder."""
    r = agent.retriever
    if r.source_count == 0:
        console.print("[dim]Knowledge base is empty. Use [bold]/learn <path>[/bold] to index documents.[/dim]")
        return

    # Group sources by their parent directory
    from collections import defaultdict
    by_folder: dict[str, list[str]] = defaultdict(list)
    for src in r.sources:
        parent = str(Path(src).parent)
        by_folder[parent].append(Path(src).name)

    # Folders table
    folders_t = Table(show_header=True, box=None, padding=(0, 2))
    folders_t.add_column("Folder", style="cyan")
    folders_t.add_column("Files", style="bold", justify="right")
    for folder in sorted(by_folder.keys()):
        folders_t.add_row(folder, str(len(by_folder[folder])))

    console.print(Panel(
        folders_t,
        title=f"[bold]Knowledge base — folders[/bold]  ·  {len(by_folder)} folder(s) · {r.source_count} files · {r.chunk_count} chunks",
        border_style="cyan",
        padding=(0, 1),
    ))
    console.print("[dim]  Use [bold]/knowledge files[/bold] to see the full list of indexed files[/dim]")


def _cmd_knowledge_files(agent: Agent) -> None:
    """Show the full list of individual files tracked in the knowledge base."""
    r = agent.retriever
    if r.source_count == 0:
        console.print("[dim]Knowledge base is empty. Use [bold]/learn <path>[/bold] to index documents.[/dim]")
        return

    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column(style="cyan")
    for src in r.sources:
        t.add_row(src)
    console.print(Panel(
        t,
        title=f"[bold]Knowledge base — files[/bold]  ·  {r.source_count} files · {r.chunk_count} chunks",
        border_style="cyan",
        padding=(0, 1),
    ))


def _cmd_mcp(agent: Agent, args: str) -> None:
    """Dispatcher for the /mcp subcommands."""
    from .mcp_client import load_mcp_config, save_mcp_config, config_path

    tokens = args.split() if args else []
    sub = tokens[0].lower() if tokens else "list"

    if sub == "list":
        servers = agent.mcp.list_servers()
        if not servers:
            console.print(f"[dim]Nessun server MCP configurato.[/dim]")
            console.print(f"[dim]  Config file: {config_path()}[/dim]")
            console.print(f"[dim]  Aggiungi con: /mcp add <nome> <comando> [args...][/dim]")
        else:
            t = Table(show_header=True, box=None, padding=(0, 2))
            t.add_column("Server", style="bold cyan")
            t.add_column("Stato", style="bold")
            t.add_column("Tool", justify="right")
            t.add_column("Comando", style="dim")
            for s in servers:
                if not s["enabled"]:
                    status = "[dim]disabilitato[/dim]"
                elif s["connected"]:
                    status = "[green]● connesso[/green]"
                else:
                    status = "[red]● errore[/red]"
                cmd_str = s["command"] + (" " + " ".join(s["args"]) if s["args"] else "")
                t.add_row(s["name"], status, str(s["n_tools"]), cmd_str[:60])
            console.print(Panel(t, title="[bold]Server MCP[/bold]", border_style="cyan", padding=(0, 1)))
        if agent.mcp.errors:
            for err in agent.mcp.errors:
                console.print(f"[yellow]⚠[/yellow] [dim]{err}[/dim]")

    elif sub == "tools":
        tools = agent.mcp.list_tools()
        if not tools:
            console.print("[dim]Nessun tool MCP disponibile.[/dim]")
            return
        t = Table(show_header=True, box=None, padding=(0, 2))
        t.add_column("Tool", style="bold cyan")
        t.add_column("Server", style="dim")
        t.add_column("Descrizione")
        for name, server, desc in tools:
            t.add_row(name, server, desc)
        console.print(Panel(t, title="[bold]Tool MCP[/bold]", border_style="cyan", padding=(0, 1)))

    elif sub in ("enable", "disable") and len(tokens) >= 2:
        name = tokens[1]
        cfg = load_mcp_config()
        if name not in cfg.get("mcpServers", {}):
            console.print(f"[red]Server '{name}' non trovato nel config.[/red]")
            return
        cfg["mcpServers"][name]["enabled"] = (sub == "enable")
        save_mcp_config(cfg)
        state = "abilitato" if sub == "enable" else "disabilitato"
        console.print(f"[dim]Server '{name}' {state}. Usa /mcp reload per applicare.[/dim]")

    elif sub == "add" and len(tokens) >= 3:
        name = tokens[1]
        command = tokens[2]
        srv_args = tokens[3:]
        cfg = load_mcp_config()
        cfg.setdefault("mcpServers", {})[name] = {
            "command": command,
            "args": srv_args,
            "enabled": True,
        }
        save_mcp_config(cfg)
        console.print(f"[green]✓[/green] Server '{name}' aggiunto. Usa [bold]/mcp reload[/bold] per avviarlo.")

    elif sub == "remove" and len(tokens) >= 2:
        name = tokens[1]
        cfg = load_mcp_config()
        if cfg.get("mcpServers", {}).pop(name, None) is not None:
            save_mcp_config(cfg)
            console.print(f"[dim]Server '{name}' rimosso. Usa /mcp reload per applicare.[/dim]")
        else:
            console.print(f"[red]Server '{name}' non trovato.[/red]")

    elif sub == "reload":
        console.print("[dim]Riavvio server MCP...[/dim]")
        agent.mcp.shutdown()
        # Recreate manager (fresh event loop) and restart
        from .mcp_client import MCPManager
        agent.mcp = MCPManager()
        agent.mcp.start()
        n_servers = len([s for s in agent.mcp.list_servers() if s["connected"]])
        n_tools = len(agent.mcp.tools)
        console.print(f"[green]✓[/green] {n_servers} server connessi, {n_tools} tool disponibili")
        for err in agent.mcp.errors:
            console.print(f"[yellow]⚠[/yellow] [dim]{err}[/dim]")

    else:
        console.print("[dim]Uso: /mcp list | tools | enable <n> | disable <n> | add <n> <cmd> [args] | remove <n> | reload[/dim]")


def _git_collect() -> tuple[bool, str, str, str, str]:
    """Return (is_repo, status_short, diff, diff_stat, recent_log)."""
    try:
        subprocess.check_output(
            ["git", "rev-parse", "--is-inside-work-tree"],
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return (False, "", "", "", "")

    def run(args: list[str]) -> str:
        try:
            return subprocess.check_output(
                args, stderr=subprocess.DEVNULL, text=True, timeout=15,
            )
        except Exception:
            return ""

    status = run(["git", "status", "--short"])
    diff_stat = run(["git", "diff", "--cached", "--stat"]) or run(["git", "diff", "--stat"])
    diff = run(["git", "diff", "--cached"]) or run(["git", "diff"])
    recent = run(["git", "log", "--oneline", "-n", "10"])
    return (True, status, diff, diff_stat, recent)


def _cmd_commit(agent: Agent) -> None:
    """Generate a commit message from current changes and commit."""
    is_repo, status, diff, diff_stat, recent_log = _git_collect()
    if not is_repo:
        console.print("[red]Non è un repository git.[/red]")
        return
    if not status.strip() and not diff.strip():
        console.print("[dim]Niente da committare — working tree pulito.[/dim]")
        return

    # Ensure there's something staged; if not, offer to stage everything
    try:
        staged = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only"],
            stderr=subprocess.DEVNULL, text=True, timeout=10,
        ).strip()
    except Exception:
        staged = ""

    if not staged:
        console.print("[dim]Nessun file in staging.[/dim]")
        preview = Table(show_header=False, box=None, padding=(0, 2))
        preview.add_column(style="cyan")
        for line in status.splitlines():
            preview.add_row(line)
        console.print(Panel(preview, title="[bold]git status[/bold]", border_style="cyan", padding=(0, 1)))
        try:
            ans = input("  Fare 'git add -A' di tutti i file mostrati? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if ans not in ("y", "yes", "s", "si", "sì"):
            console.print("[dim]Annullato — aggiungi manualmente i file con 'git add'.[/dim]")
            return
        try:
            subprocess.check_call(["git", "add", "-A"])
        except Exception as e:
            console.print(f"[red]git add fallito:[/red] {e}")
            return
        diff = subprocess.check_output(
            ["git", "diff", "--cached"], stderr=subprocess.DEVNULL, text=True,
        )
        diff_stat = subprocess.check_output(
            ["git", "diff", "--cached", "--stat"], stderr=subprocess.DEVNULL, text=True,
        )

    # Ask the LLM for a commit message
    console.print("[dim]Generazione messaggio di commit...[/dim]")
    try:
        with console.status("[dim]thinking...[/dim]", spinner="dots"):
            msg = agent.propose_commit_message(status, diff, recent_log)
    except Exception as e:
        console.print(f"[red]Errore generazione messaggio:[/red] {e}")
        return

    if not msg:
        console.print("[red]Il modello non ha restituito un messaggio.[/red]")
        return

    # Strip accidental code fences
    msg = msg.strip()
    if msg.startswith("```"):
        msg = msg.strip("`").strip()
        if msg.lower().startswith("text\n"):
            msg = msg[5:]

    console.print(Panel(
        msg,
        title="[bold]Messaggio di commit proposto[/bold]",
        border_style="cyan",
        padding=(0, 1),
    ))
    if diff_stat.strip():
        console.print(Panel(
            diff_stat.strip(),
            title="[bold]diff stat[/bold]",
            border_style="dim",
            padding=(0, 1),
        ))
    try:
        ans = input("  Commit? [Y/n/e=edit] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if ans in ("n", "no"):
        console.print("[dim]Commit annullato.[/dim]")
        return

    if ans in ("e", "edit"):
        try:
            new_msg = input("  Nuovo messaggio (una riga): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if new_msg:
            msg = new_msg

    try:
        subprocess.check_call(["git", "commit", "-m", msg])
        console.print("[green]✓[/green] Commit creato")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]git commit fallito:[/red] {e}")


def _cmd_undo(agent: Agent) -> None:
    """Undo the last edit_file/write_file performed by the agent."""
    size = stack_size()
    if size == 0:
        console.print("[dim]Nessuna operazione da annullare in questa sessione.[/dim]")
        return
    ok, msg = undo_last()
    if ok:
        console.print(f"[green]✓[/green] {msg}")
        remaining = stack_size()
        if remaining:
            console.print(f"[dim]  ({remaining} operazione/i ancora annullabili)[/dim]")
    else:
        console.print(f"[yellow]⚠[/yellow] {msg}")


def _cmd_compact(agent: Agent) -> None:
    """Summarize the conversation history to save context tokens."""
    if len(agent.messages) <= agent._system_prefix_count():
        console.print("[dim]Niente da compattare — la conversazione è vuota.[/dim]")
        return
    console.print("[dim]Riassumo la conversazione...[/dim]")
    try:
        with console.status("[dim]thinking...[/dim]", spinner="dots"):
            before, after, chars = agent.compact()
    except Exception as e:
        console.print(f"[red]Errore durante la compattazione:[/red] {e}")
        return
    if before == after:
        console.print("[dim]Nessun messaggio da compattare.[/dim]")
        return
    console.print(
        f"[green]✓[/green] Conversazione compattata: "
        f"[bold]{before}[/bold] → [bold]{after}[/bold] messaggi "
        f"[dim]({chars} caratteri di riassunto)[/dim]"
    )


def _cmd_costs(agent: Agent) -> None:
    """Show estimated session and weekly costs."""
    u = agent.usage

    # Session costs
    session_t = Table(show_header=True, box=None, padding=(0, 2))
    session_t.add_column("provider/model", style="bold cyan")
    session_t.add_column("input", justify="right")
    session_t.add_column("output", justify="right")
    session_t.add_column("cost", justify="right", style="bold")
    session_t.add_column("price /1M (in/out)", style="dim")

    total_session = 0.0
    if u.session_breakdown:
        for key, toks in sorted(u.session_breakdown.items()):
            provider, _, model = key.partition("/")
            cost = estimate_cost(provider, model, toks["input"], toks["output"])
            total_session += cost
            pin, pout = lookup_price(provider, model)
            session_t.add_row(
                key,
                f"{toks['input']:,}",
                f"{toks['output']:,}",
                fmt_usd(cost),
                f"${pin:.2f} / ${pout:.2f}",
            )
    else:
        session_t.add_row("—", "0", "0", fmt_usd(0.0), "—")

    session_t.add_row(
        "[bold]totale sessione[/bold]",
        f"[bold]{u.session_input:,}[/bold]",
        f"[bold]{u.session_output:,}[/bold]",
        f"[bold]{fmt_usd(total_session)}[/bold]",
        "",
    )
    console.print(Panel(session_t, title="[bold]Costi stimati — sessione[/bold]", border_style="cyan", padding=(0, 1)))

    # Weekly costs
    weekly_t = Table(show_header=True, box=None, padding=(0, 2))
    weekly_t.add_column("provider/model", style="bold cyan")
    weekly_t.add_column("input", justify="right")
    weekly_t.add_column("output", justify="right")
    weekly_t.add_column("cost", justify="right", style="bold")

    total_weekly = 0.0
    breakdown = u.weekly_breakdown
    if breakdown:
        for key, toks in sorted(breakdown.items()):
            provider, _, model = key.partition("/")
            cost = estimate_cost(provider, model, toks.get("input", 0), toks.get("output", 0))
            total_weekly += cost
            weekly_t.add_row(
                key,
                f"{toks.get('input', 0):,}",
                f"{toks.get('output', 0):,}",
                fmt_usd(cost),
            )
    else:
        weekly_t.add_row("—", "0", "0", fmt_usd(0.0))

    weekly_t.add_row(
        "[bold]totale settimana[/bold]",
        f"[bold]{sum(x.get('input', 0) for x in breakdown.values()):,}[/bold]",
        f"[bold]{sum(x.get('output', 0) for x in breakdown.values()):,}[/bold]",
        f"[bold]{fmt_usd(total_weekly)}[/bold]",
    )
    week_label = u._weekly.get("week", "?")
    console.print(Panel(weekly_t, title=f"[bold]Costi stimati — settimana {week_label}[/bold]", border_style="cyan", padding=(0, 1)))
    console.print("[dim]  Prezzi indicativi (USD per 1M token). Modifica ~/.ollama_agent_prices.json per personalizzarli.[/dim]")


def _cmd_init(agent: Agent) -> None:
    """Create or open AGENT.md in the current directory."""
    path = Path(os.getcwd()) / "AGENT.md"
    if path.exists():
        console.print(f"[dim]AGENT.md already exists in {os.getcwd()}[/dim]")
        return
    template = (
        "# Project context\n\n"
        "<!-- Describe the project so Ollama Agent understands it from the start. -->\n\n"
        "## Description\n\n\n"
        "## Stack\n\n\n"
        "## Conventions\n\n\n"
        "## Notes\n\n"
    )
    path.write_text(template, encoding="utf-8")
    agent.refresh_context()
    console.print(f"[green]✓[/green] Created [bold]AGENT.md[/bold] in {os.getcwd()}")
    console.print("[dim]Edit it to add project context — reloaded automatically on every message.[/dim]")


def run_interactive(agent: Agent) -> None:
    console.print(Panel(BANNER, border_style="cyan", padding=(0, 1)))
    console.print(
        f"[dim]  provider: {agent.config.provider} | model: {agent.config.model}[/dim]"
    )
    console.print()

    def toolbar():
        txt = agent.usage.toolbar_text()
        if not txt:
            return HTML(f"<ansigray> {agent.config.model}</ansigray>")
        return HTML(f"<ansigray> {agent.config.model}  │  {txt}</ansigray>")

    def _auto_save_on_exit():
        if load_auto_save_pref() and len(agent.messages) > 2:
            path = save_session(agent)
            console.print(f"[dim]Auto-saved: {path.name}[/dim]")

    history_path = Path.home() / ".ollama_agent_history"
    session: PromptSession = PromptSession(
        history=FileHistory(str(history_path)),
        auto_suggest=AutoSuggestFromHistory(),
        completer=SlashCompleter(),
        complete_while_typing=True,
        style=PROMPT_STYLE,
        bottom_toolbar=toolbar,
    )

    while True:
        try:
            raw = session.prompt(HTML("<bold><cyan>> </cyan></bold>")).strip()
        except KeyboardInterrupt:
            continue
        except EOFError:
            _auto_save_on_exit()
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not raw:
            continue

        if not raw.startswith("/"):
            try:
                agent.chat(raw)
            except KeyboardInterrupt:
                console.print("\n[dim]Interrupted.[/dim]")
                if agent.messages and agent.messages[-1]["role"] == "user":
                    agent.messages.pop()
            continue

        # --- Slash commands ---
        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()

        if cmd in ("/exit", "/quit"):
            _auto_save_on_exit()
            console.print("[dim]Goodbye![/dim]")
            break

        elif cmd == "/help":
            _show_help()

        elif cmd == "/clear":
            agent.messages = agent.messages[:2]  # keep system prompt + context
            agent.refresh_context()
            console.print("[dim]Conversation cleared.[/dim]")

        elif cmd == "/settings":
            _show_settings(agent)

        elif cmd == "/init":
            _cmd_init(agent)

        elif cmd == "/learn":
            if len(parts) > 1:
                # Parse optional --force / -f flag
                tokens = parts[1].strip().split()
                force = False
                path_tokens = []
                for t in tokens:
                    if t in ("--force", "-f", "force"):
                        force = True
                    else:
                        path_tokens.append(t)
                if path_tokens:
                    _cmd_learn(agent, " ".join(path_tokens), force=force)
                else:
                    console.print("[red]Usage:[/red] /learn <file-or-directory> [--force]")
            else:
                console.print("[red]Usage:[/red] /learn <file-or-directory> [--force]")

        elif cmd == "/knowledge":
            if len(parts) > 1 and parts[1].strip().lower() == "files":
                _cmd_knowledge_files(agent)
            else:
                _cmd_knowledge(agent)

        elif cmd == "/tools":
            _show_tools()

        elif cmd == "/model":
            if len(parts) > 1:
                agent.config.model = parts[1].strip()
                save_user_prefs(agent.config.provider, agent.config.model)
                console.print(f"[dim]Model switched to: {agent.config.model} (saved as default)[/dim]")
            else:
                console.print(f"[dim]Current model: {agent.config.model}[/dim]")

        elif cmd == "/models":
            models = _list_ollama_models()
            if models:
                t = Table(show_header=False, box=None, padding=(0, 2))
                t.add_column(style="cyan")
                for m in models:
                    marker = " [green]●[/green]" if m == agent.config.model else ""
                    t.add_row(m + marker)
                console.print(Panel(t, title="[bold]Ollama models[/bold]", border_style="cyan", padding=(0, 1)))
            else:
                console.print("[dim]No models found (is Ollama running?)[/dim]")

        elif cmd == "/provider":
            if len(parts) > 1:
                new_provider = parts[1].strip()
                if new_provider not in PROVIDERS:
                    console.print(f"[red]Unknown provider:[/red] {new_provider}. Choose from: {', '.join(PROVIDERS)}")
                else:
                    new_config = Config.from_env(provider=new_provider)
                    agent.config = new_config
                    save_user_prefs(new_config.provider, new_config.model)
                    console.print(f"[dim]Switched to {new_provider} / {new_config.model} (saved as default)[/dim]")
            else:
                console.print(f"[dim]Current provider: {agent.config.provider}[/dim]")

        elif cmd == "/routing":
            if len(parts) > 1:
                mode = parts[1].strip().lower()
                if mode not in ROUTING_MODES:
                    console.print(f"[red]Unknown mode:[/red] {mode}. Choose from: {', '.join(ROUTING_MODES)}")
                else:
                    agent.routing_mode = mode
                    save_routing_mode(mode)
                    labels = {"manual": "Single model (you choose)", "auto": "Auto-classifier routes to best model", "static": "Static rules (task → model)"}
                    console.print(f"[dim]Routing mode: [bold]{mode}[/bold] — {labels[mode]} (saved)[/dim]")
                    if mode == "static":
                        _show_rules(agent)
            else:
                console.print(f"[dim]Current routing: [bold]{agent.routing_mode}[/bold][/dim]")
                console.print(f"[dim]  Use /routing manual|auto|static to change[/dim]")

        elif cmd == "/rules":
            if len(parts) > 1:
                sub = parts[1].strip()
                if sub == "reset":
                    from .config import DEFAULT_STATIC_RULES
                    agent.static_rules = dict(DEFAULT_STATIC_RULES)
                    save_static_rules(agent.static_rules)
                    console.print("[dim]Static rules reset to defaults.[/dim]")
                    _show_rules(agent)
                elif sub == "list":
                    _show_rules(agent)
                elif "=" in sub:
                    # /rules code=deepseek-coder-v2
                    key, val = sub.split("=", 1)
                    key = key.strip().lower()
                    val = val.strip()
                    if key not in TASK_CATEGORIES:
                        console.print(f"[red]Unknown category:[/red] {key}. Choose from: {', '.join(TASK_CATEGORIES)}")
                    elif not val:
                        console.print(f"[red]Model name cannot be empty[/red]")
                    else:
                        agent.static_rules[key] = val
                        save_static_rules(agent.static_rules)
                        console.print(f"[dim]Rule updated: [bold]{key}[/bold] → {val} (saved)[/dim]")
                else:
                    console.print("[red]Usage:[/red] /rules list | /rules reset | /rules <category>=<model>")
            else:
                _show_rules(agent)

        elif cmd == "/save":
            if len(agent.messages) <= 2:
                console.print("[dim]Nothing to save — conversation is empty.[/dim]")
            else:
                title = parts[1].strip() if len(parts) > 1 else None
                path = save_session(agent, title=title)
                console.print(f"[green]✓[/green] Session saved: [bold]{path.name}[/bold]")

        elif cmd == "/sessions":
            sessions = list_sessions()
            if not sessions:
                console.print("[dim]No saved sessions. Use [bold]/save[/bold] to save one.[/dim]")
            else:
                st = Table(show_header=True, box=None, padding=(0, 2))
                st.add_column("#", style="bold cyan", justify="right")
                st.add_column("Title", style="bold")
                st.add_column("Directory", style="dim")
                st.add_column("Date", style="dim")
                st.add_column("Msgs", justify="right")
                for s in sessions:
                    cwd_short = s.get("cwd", "—")
                    home = str(Path.home())
                    if cwd_short.startswith(home):
                        cwd_short = "~" + cwd_short[len(home):]
                    st.add_row(
                        str(s["index"]),
                        s.get("title", "—"),
                        cwd_short,
                        s.get("timestamp", "")[:16].replace("T", " "),
                        str(s.get("message_count", "?")),
                    )
                console.print(Panel(st, title="[bold]Saved sessions[/bold]", border_style="cyan", padding=(0, 1)))

        elif cmd == "/resume":
            idx = None
            if len(parts) > 1:
                try:
                    idx = int(parts[1].strip())
                except ValueError:
                    console.print("[red]Usage:[/red] /resume [number]")
                    continue
            data = load_session(idx)
            if data is None:
                console.print("[dim]No session found.[/dim]")
            else:
                agent.messages = data["messages"]
                agent.refresh_context()
                console.print(
                    f"[green]✓[/green] Resumed: [bold]{data['title']}[/bold]  "
                    f"[dim]({data.get('timestamp', '')[:16].replace('T', ' ')}, "
                    f"{data.get('message_count', '?')} messages)[/dim]"
                )

        elif cmd == "/autosave":
            current = load_auto_save_pref()
            new_val = not current
            save_auto_save_pref(new_val)
            state = "ON" if new_val else "OFF"
            console.print(f"[dim]Auto-save on exit: [bold]{state}[/bold] (saved)[/dim]")

        elif cmd == "/ask":
            if len(parts) < 2 or len(parts[1].split(maxsplit=1)) < 2:
                console.print("[red]Usage:[/red] /ask <file> <question>")
            else:
                file_arg, question = parts[1].split(maxsplit=1)
                prompt_text = (
                    f"Usando esclusivamente il file '{file_arg}' dalla knowledge base "
                    f"(passa '{file_arg}' come source_filter a search_knowledge), "
                    f"rispondi: {question}"
                )
                try:
                    agent.chat(prompt_text)
                except KeyboardInterrupt:
                    console.print("\n[dim]Interrupted.[/dim]")
                    if agent.messages and agent.messages[-1]["role"] == "user":
                        agent.messages.pop()

        elif cmd == "/ragmode":
            if len(parts) > 1:
                mode = parts[1].strip().lower()
                if mode not in RAG_MODES:
                    console.print(f"[red]Unknown mode:[/red] {mode}. Choose from: {', '.join(RAG_MODES)}")
                else:
                    agent.rag_mode = mode
                    save_rag_mode(mode)
                    agent.refresh_context()
                    labels = {
                        "standard": "Top-k fast retrieval (default)",
                        "rlm": "Recursive LM — scans every chunk via recursive LLM calls",
                    }
                    console.print(f"[dim]RAG mode: [bold]{mode}[/bold] — {labels[mode]} (saved)[/dim]")
            else:
                console.print(f"[dim]Current RAG mode: [bold]{agent.rag_mode}[/bold][/dim]")
                console.print(f"[dim]  Use /ragmode standard|rlm to change[/dim]")

        elif cmd == "/mcp":
            _cmd_mcp(agent, parts[1] if len(parts) > 1 else "")

        elif cmd == "/web":
            sub = parts[1].strip().lower() if len(parts) > 1 else ""
            if not sub:
                state = "ON" if agent.web_enabled else "OFF"
                console.print(f"[dim]Web access: [bold]{state}[/bold]  ·  provider: [bold]{agent.web_provider}[/bold][/dim]")
                console.print("[dim]  Usage: /web on | /web off | /web provider <duckduckgo|brave|tavily>[/dim]")
            elif sub == "on":
                agent.web_enabled = True
                save_web_enabled(True)
                console.print(f"[dim]Web access: [bold]ON[/bold] (provider: {agent.web_provider}) — saved[/dim]")
            elif sub == "off":
                agent.web_enabled = False
                save_web_enabled(False)
                console.print("[dim]Web access: [bold]OFF[/bold] — saved[/dim]")
            elif sub.startswith("provider"):
                tokens = sub.split(None, 1)
                if len(tokens) < 2:
                    console.print(f"[dim]Current provider: [bold]{agent.web_provider}[/bold]  ·  available: {', '.join(WEB_PROVIDERS)}[/dim]")
                else:
                    name = tokens[1].strip()
                    if name not in WEB_PROVIDERS:
                        console.print(f"[red]Unknown provider:[/red] {name}. Choose from: {', '.join(WEB_PROVIDERS)}")
                    else:
                        agent.web_provider = name
                        save_web_provider(name)
                        console.print(f"[dim]Web provider: [bold]{name}[/bold] (saved)[/dim]")
                        if name == "brave" and not os.getenv("BRAVE_API_KEY"):
                            console.print("[yellow]  ⚠ BRAVE_API_KEY not set — get a free key at https://brave.com/search/api[/yellow]")
                        elif name == "tavily" and not os.getenv("TAVILY_API_KEY"):
                            console.print("[yellow]  ⚠ TAVILY_API_KEY not set — get a free key at https://tavily.com[/yellow]")
            else:
                console.print("[red]Usage:[/red] /web on | /web off | /web provider <duckduckgo|brave|tavily>")

        elif cmd == "/lang":
            if len(parts) > 1:
                new_lang = parts[1].strip().lower()
                if new_lang not in LANGUAGES:
                    console.print(f"[red]Lingua non valida:[/red] {new_lang}. Scegli tra: {', '.join(LANGUAGES)}")
                else:
                    save_language(new_lang)
                    msg = (
                        f"[dim]Lingua interfaccia: [bold]{new_lang}[/bold] (salvata)[/dim]"
                        if new_lang == "it"
                        else f"[dim]Interface language: [bold]{new_lang}[/bold] (saved)[/dim]"
                    )
                    console.print(msg)
            else:
                current = load_language()
                console.print(f"[dim]Lingua corrente: [bold]{current}[/bold] — usa /lang it|en[/dim]")

        elif cmd == "/voice":
            from .voice import record_and_transcribe
            console.print("[cyan]🎙️  Parla ora — premi Invio per terminare la registrazione...[/cyan]")
            text, err = record_and_transcribe()
            if err:
                console.print(f"[red]{err}[/red]")
            elif not text:
                console.print("[yellow]Nessun audio rilevato.[/yellow]")
            else:
                console.print(f"[dim]Trascrizione:[/dim] [bold cyan]{text}[/bold cyan]")
                try:
                    agent.chat(text)
                except KeyboardInterrupt:
                    console.print("\n[dim]Interrupted.[/dim]")
                    if agent.messages and agent.messages[-1]["role"] == "user":
                        agent.messages.pop()

        elif cmd == "/compact":
            _cmd_compact(agent)

        elif cmd == "/commit":
            _cmd_commit(agent)

        elif cmd == "/undo":
            _cmd_undo(agent)

        elif cmd == "/costs":
            _cmd_costs(agent)

        elif cmd == "/quiet":
            agent.quiet_mode = not agent.quiet_mode
            save_quiet_pref(agent.quiet_mode)
            state = "ON" if agent.quiet_mode else "OFF"
            console.print(f"[dim]Quiet mode: [bold]{state}[/bold] (saved)[/dim]")

        elif cmd == "/auto":
            agent.auto_approve = True
            console.print("[dim]Auto-approve enabled. Tool operations will execute without asking.[/dim]")

        elif cmd == "/manual":
            agent.auto_approve = False
            console.print("[dim]Manual mode enabled. Write/execute operations will ask for consent.[/dim]")

        else:
            console.print(f"[red]Unknown command:[/red] {cmd}  (type [bold]/help[/bold] for the list)")


@click.command()
@click.option(
    "--provider", "-p",
    default=None,
    type=click.Choice(list(PROVIDERS.keys())),
    show_default=True,
    help="LLM provider (default: saved preference or ollama)",
)
@click.option("--model", "-m", default=None, help="Model name (overrides provider default)")
@click.option("--base-url", default=None, help="Custom API base URL")
@click.option("--api-key", default=None, help="API key (overrides env var)")
@click.argument("prompt", required=False)
def cli(provider: str, model: str, base_url: str, api_key: str, prompt: str) -> None:
    """Ollama Agent — AI-powered coding assistant for the terminal."""
    config = Config.from_env(provider=provider, model=model)

    if base_url:
        config.base_url = base_url
    if api_key:
        config.api_key = api_key

    if not config.api_key and provider != "ollama":
        env_key = PROVIDERS[provider]["env_key"]
        console.print(
            f"[red]Error:[/red] No API key found. "
            f"Set the [bold]{env_key}[/bold] environment variable or use --api-key."
        )
        sys.exit(1)

    agent = Agent(config)

    if prompt:
        try:
            agent.chat(prompt)
        except KeyboardInterrupt:
            pass
        return

    run_interactive(agent)
