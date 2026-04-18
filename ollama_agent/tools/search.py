import subprocess
import glob as glob_module
from pathlib import Path


def grep(
    pattern: str,
    path: str = ".",
    glob_pattern: str = None,
    case_insensitive: bool = False,
) -> str:
    """Search for a regex pattern in files."""
    try:
        cmd = ["grep", "-rn", "--color=never"]
        if case_insensitive:
            cmd.append("-i")
        if glob_pattern:
            cmd.extend(["--include", glob_pattern])
        cmd.extend([pattern, path])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = result.stdout.strip()

        if not output:
            return "No matches found"

        lines = output.split("\n")
        if len(lines) > 100:
            truncated = lines[:100]
            truncated.append(f"... ({len(lines) - 100} more matches)")
            return "\n".join(truncated)
        return output
    except Exception as e:
        return f"Error searching: {e}"


def find_files(pattern: str, path: str = ".") -> str:
    """Find files matching a glob pattern."""
    try:
        base = Path(path)
        search = str(base / pattern)
        matches = sorted(glob_module.glob(search, recursive=True))

        if not matches:
            return "No files found matching pattern"

        if len(matches) > 100:
            result = "\n".join(matches[:100])
            result += f"\n... ({len(matches) - 100} more files)"
            return result
        return "\n".join(matches)
    except Exception as e:
        return f"Error finding files: {e}"
