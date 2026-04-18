from .bash import run_bash
from .files import read_file, write_file, edit_file, list_dir
from .search import grep, find_files

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": (
                "Execute a bash command and return its output. "
                "Use for running scripts, tests, git operations, installing packages, etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The bash command to execute"},
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 30)",
                        "default": 30,
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file and return its contents with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file. Creates it if it doesn't exist, overwrites if it does.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": (
                "Replace an exact string in a file. "
                "The old_string must appear exactly once in the file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"},
                    "old_string": {
                        "type": "string",
                        "description": "Exact string to replace (must be unique in the file)",
                    },
                    "new_string": {"type": "string", "description": "Replacement string"},
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List the contents of a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path (default: current directory)",
                        "default": ".",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": "Search for a regex pattern in files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern to search for"},
                    "path": {
                        "type": "string",
                        "description": "Directory or file to search in (default: .)",
                        "default": ".",
                    },
                    "glob_pattern": {
                        "type": "string",
                        "description": "Filter files by glob (e.g. '*.py', '*.{ts,tsx}')",
                    },
                    "case_insensitive": {
                        "type": "boolean",
                        "description": "Case insensitive search",
                        "default": False,
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_files",
            "description": "Find files matching a glob pattern.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern (e.g. '**/*.py', 'src/**/*.ts')",
                    },
                    "path": {
                        "type": "string",
                        "description": "Base directory to search in (default: .)",
                        "default": ".",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "deep_query",
            "description": (
                "Recursive retrieval (RLM): scans ALL chunks of the selected files, "
                "using the LLM itself to extract only the parts relevant to the question. "
                "Slower than search_knowledge but preserves global context — use it for "
                "long documents, comparative questions, or when top-k retrieval misses "
                "the whole picture. If the user asks about a specific file, pass its name "
                "as 'source_filter'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to answer from the knowledge base",
                    },
                    "source_filter": {
                        "type": "string",
                        "description": "Optional: restrict to files whose name contains this substring",
                    },
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": (
                "Search the local knowledge base for relevant information. "
                "Use this when the user asks about something that might be in indexed documents, "
                "internal docs, or files previously learned with /learn. "
                "IMPORTANT: When the user mentions a specific file (e.g. 'dimmi cosa dice il file X.pdf' "
                "or 'riassumi il documento autore.pdf'), ALWAYS pass the filename (or a distinctive "
                "substring of it) as the 'source_filter' argument, so the search is restricted to that "
                "specific file. Otherwise the results may come from any file in the KB. "
                "The results already contain the relevant text extracted from the original files. "
                "Do NOT use read_file on the source files after searching — the chunks returned here "
                "are the content you need. Reading the original files (especially PDFs) would be redundant "
                "and may exceed the context limit."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query (what you want to find in the documents)",
                    },
                    "k": {
                        "type": "integer",
                        "description": "Number of results to return (default: 5)",
                        "default": 5,
                    },
                    "source_filter": {
                        "type": "string",
                        "description": (
                            "Optional: restrict search to files whose path or filename contains this "
                            "substring (case-insensitive). Use this when the user asks about a specific "
                            "file (e.g. source_filter='McMillan' will only return chunks from files "
                            "with 'McMillan' in the name)."
                        ),
                    },
                },
                "required": ["query"],
            },
        },
    },
]


def execute_tool(name: str, args: dict, retriever=None, llm_client=None, llm_model=None) -> str:
    """Dispatch a tool call by name."""
    try:
        return _dispatch(name, args, retriever, llm_client, llm_model)
    except KeyError as e:
        return f"Error: missing required argument {e} for tool '{name}'"
    except Exception as e:
        return f"Error executing tool '{name}': {e}"


def _dispatch(name: str, args: dict, retriever=None, llm_client=None, llm_model=None) -> str:
    if name == "bash":
        return run_bash(args["command"], args.get("timeout", 30))
    elif name == "read_file":
        return read_file(args["path"])
    elif name == "write_file":
        return write_file(args["path"], args["content"])
    elif name == "edit_file":
        return edit_file(args["path"], args["old_string"], args["new_string"])
    elif name == "list_dir":
        return list_dir(args.get("path", "."))
    elif name == "grep":
        return grep(
            args["pattern"],
            args.get("path", "."),
            args.get("glob_pattern"),
            args.get("case_insensitive", False),
        )
    elif name == "find_files":
        return find_files(args["pattern"], args.get("path", "."))
    elif name == "search_knowledge":
        if retriever is None:
            return "Knowledge base not available."
        return retriever.search(
            args["query"],
            k=args.get("k", 5),
            source_filter=args.get("source_filter"),
        )
    elif name == "deep_query":
        if retriever is None:
            return "Knowledge base not available."
        if llm_client is None or llm_model is None:
            return "deep_query requires an LLM client (internal error)."
        from ..rag.rlm import deep_query as _deep_query
        return _deep_query(
            retriever, llm_client, llm_model,
            question=args["question"],
            source_filter=args.get("source_filter"),
        )
    else:
        return f"Unknown tool: {name}"
