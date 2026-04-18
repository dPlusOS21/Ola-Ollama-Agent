from pathlib import Path


def read_file(path: str) -> str:
    """Read a file and return its contents with line numbers."""
    try:
        p = Path(path)
        if not p.exists():
            return f"Error: File not found: {path}"
        if not p.is_file():
            return f"Error: Not a file: {path}"
        content = p.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        numbered = "\n".join(f"{i + 1}\t{line}" for i, line in enumerate(lines))
        return numbered
    except Exception as e:
        return f"Error reading file: {e}"


def write_file(path: str, content: str) -> str:
    """Write content to a file, creating it if it doesn't exist."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} characters to {path}"
    except Exception as e:
        return f"Error writing file: {e}"


def edit_file(path: str, old_string: str, new_string: str) -> str:
    """Replace an exact string in a file (must be unique)."""
    try:
        p = Path(path)
        if not p.exists():
            return f"Error: File not found: {path}"
        content = p.read_text(encoding="utf-8")
        count = content.count(old_string)
        if count == 0:
            return f"Error: String not found in {path}"
        if count > 1:
            return f"Error: String found {count} times in {path}. Make old_string more unique."
        new_content = content.replace(old_string, new_string, 1)
        p.write_text(new_content, encoding="utf-8")
        return f"Successfully edited {path}"
    except Exception as e:
        return f"Error editing file: {e}"


def list_dir(path: str = ".") -> str:
    """List the contents of a directory."""
    try:
        p = Path(path)
        if not p.exists():
            return f"Error: Path not found: {path}"
        if not p.is_dir():
            return f"Error: Not a directory: {path}"
        items = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        lines = []
        for item in items:
            if item.name.startswith("."):
                continue
            if item.is_dir():
                lines.append(f"{item.name}/")
            else:
                size = item.stat().st_size
                lines.append(f"{item.name} ({size:,} bytes)")
        return "\n".join(lines) if lines else "Empty directory"
    except Exception as e:
        return f"Error listing directory: {e}"
