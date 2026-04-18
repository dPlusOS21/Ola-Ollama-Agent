"""MCP (Model Context Protocol) client integration.

Runs all async MCP work on a dedicated background event loop so the rest of
ola can call sync methods without caring about asyncio. Tools exposed by
MCP servers are namespaced ``mcp__<server>__<tool>`` to avoid collisions
with the built-in tools.

Config file (Claude Desktop compatible):
    ~/.ollama_agent_mcp.json
    {
      "mcpServers": {
        "filesystem": {
          "command": "npx",
          "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
          "enabled": true
        }
      }
    }
"""

from __future__ import annotations

import asyncio
import json
import threading
from pathlib import Path
from typing import Any

_CONFIG_FILE = Path.home() / ".ollama_agent_mcp.json"


def config_path() -> Path:
    return _CONFIG_FILE


def load_mcp_config() -> dict:
    if not _CONFIG_FILE.exists():
        return {"mcpServers": {}}
    try:
        data = json.loads(_CONFIG_FILE.read_text())
        if "mcpServers" not in data:
            data["mcpServers"] = {}
        return data
    except Exception:
        return {"mcpServers": {}}


def save_mcp_config(cfg: dict) -> None:
    _CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


class MCPManager:
    """Manage MCP server subprocesses and expose their tools to ola."""

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()

        self._sessions: dict[str, Any] = {}
        self._exit_stacks: dict[str, Any] = {}

        # OpenAI-style tool definitions ready to be merged into TOOL_DEFINITIONS
        self.tools: list[dict] = []
        self._tool_to_server: dict[str, str] = {}
        self._tool_orig_names: dict[str, str] = {}
        self.errors: list[str] = []
        self.available = True  # becomes False if the mcp package is missing

    # ── Event loop plumbing ─────────────────────────────────────────────

    def _ensure_loop(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=5)

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._ready.set()
        self._loop.run_forever()

    def _submit(self, coro) -> Any:
        assert self._loop is not None
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result()

    # ── Lifecycle ───────────────────────────────────────────────────────

    def start(self, config: dict | None = None) -> None:
        """Launch enabled servers and discover their tools. Safe to call once."""
        self._ensure_loop()
        cfg = config if config is not None else load_mcp_config()
        try:
            self._submit(self._load_servers_async(cfg))
        except Exception as e:
            self.errors.append(f"MCP init error: {e}")

    async def _load_servers_async(self, config: dict) -> None:
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            from contextlib import AsyncExitStack
        except ImportError:
            self.available = False
            self.errors.append(
                "Pacchetto 'mcp' non installato. Installa con: pip install mcp"
            )
            return

        servers = config.get("mcpServers", {})
        for name, spec in servers.items():
            if not spec.get("enabled", True):
                continue
            try:
                stack = AsyncExitStack()
                params = StdioServerParameters(
                    command=spec["command"],
                    args=spec.get("args", []),
                    env=spec.get("env"),
                )
                transport = await stack.enter_async_context(stdio_client(params))
                read, write = transport
                session = await stack.enter_async_context(ClientSession(read, write))
                await session.initialize()

                self._sessions[name] = session
                self._exit_stacks[name] = stack

                tools_result = await session.list_tools()
                for t in tools_result.tools:
                    namespaced = f"mcp__{name}__{t.name}"
                    schema = t.inputSchema or {"type": "object", "properties": {}}
                    self.tools.append({
                        "type": "function",
                        "function": {
                            "name": namespaced,
                            "description": (t.description or f"MCP tool '{t.name}' from server '{name}'")[:1000],
                            "parameters": schema,
                        },
                    })
                    self._tool_to_server[namespaced] = name
                    self._tool_orig_names[namespaced] = t.name
            except Exception as e:
                self.errors.append(f"MCP server '{name}' failed: {e}")

    def shutdown(self) -> None:
        if self._loop is None:
            return
        try:
            self._submit(self._shutdown_async())
        except Exception:
            pass
        try:
            self._loop.call_soon_threadsafe(self._loop.stop)
        except Exception:
            pass

    async def _shutdown_async(self) -> None:
        for stack in list(self._exit_stacks.values()):
            try:
                await stack.aclose()
            except Exception:
                pass
        self._exit_stacks.clear()
        self._sessions.clear()

    # ── Dispatch ────────────────────────────────────────────────────────

    def is_mcp_tool(self, name: str) -> bool:
        return name in self._tool_to_server

    def call_tool(self, name: str, args: dict) -> str:
        server = self._tool_to_server.get(name)
        if not server:
            return f"Errore: tool MCP '{name}' non trovato"
        orig = self._tool_orig_names[name]
        try:
            return self._submit(self._call_tool_async(server, orig, args))
        except Exception as e:
            return f"Errore chiamata MCP '{name}': {e}"

    async def _call_tool_async(self, server: str, tool: str, args: dict) -> str:
        session = self._sessions.get(server)
        if session is None:
            return f"Server MCP '{server}' non connesso"
        result = await session.call_tool(tool, args)
        parts: list[str] = []
        for c in getattr(result, "content", []) or []:
            if hasattr(c, "text") and c.text:
                parts.append(c.text)
            else:
                parts.append(str(c))
        return "\n".join(parts) or "(nessun contenuto)"

    # ── Introspection for /mcp list ─────────────────────────────────────

    def list_servers(self) -> list[dict]:
        cfg = load_mcp_config()
        out = []
        for name, spec in cfg.get("mcpServers", {}).items():
            enabled = spec.get("enabled", True)
            connected = name in self._sessions
            n_tools = sum(
                1 for t in self.tools
                if self._tool_to_server.get(t["function"]["name"]) == name
            )
            out.append({
                "name": name,
                "enabled": enabled,
                "connected": connected,
                "n_tools": n_tools,
                "command": spec.get("command", ""),
                "args": spec.get("args", []),
            })
        return out

    def list_tools(self) -> list[tuple[str, str, str]]:
        """Return (namespaced_name, server, description) for /mcp tools."""
        out = []
        for t in self.tools:
            name = t["function"]["name"]
            out.append((
                name,
                self._tool_to_server.get(name, "?"),
                t["function"].get("description", "")[:80],
            ))
        return out
