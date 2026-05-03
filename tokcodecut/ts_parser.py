import json
import subprocess
from pathlib import Path
from .models import err_not_found, err_symbol_not_found, err_no_node, err_parse

_LENS = Path(__file__).parent.parent / "node" / "ts_lens.mjs"


def _run(operation: str, path: str, *extra: str) -> str:
    try:
        proc = subprocess.run(
            ["node", str(_LENS), operation, path, *extra],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        return err_no_node()
    except subprocess.TimeoutExpired:
        return err_parse(path, "timeout")

    raw = proc.stdout.strip()
    if not raw:
        return err_parse(path, "no output from ts_lens")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return err_parse(path, "invalid JSON from ts_lens")

    if "error" in data:
        return err_parse(path, data["error"])
    return data.get("result", "")


def structure(path: str) -> str:
    """Returns flat symbol name list for TypeScript/JS/Svelte file."""
    if not Path(path).exists():
        return err_not_found(path)
    return _run("structure", path)


def skeleton(path: str) -> str:
    """Returns all signatures + first JSDoc line, no bodies."""
    if not Path(path).exists():
        return err_not_found(path)
    return _run("skeleton", path)


def symbol_body(path: str, name: str) -> str:
    """Returns full source of one named symbol."""
    if not Path(path).exists():
        return err_not_found(path)
    result = _run("body", path, name)
    if not result:
        return err_symbol_not_found(name, path)
    return result


def imports(path: str) -> str:
    """Returns import declarations only."""
    if not Path(path).exists():
        return err_not_found(path)
    return _run("imports", path)
