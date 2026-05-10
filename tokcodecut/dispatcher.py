import os
import re
from pathlib import Path
from .models import PY_EXTENSIONS, TS_EXTENSIONS, CONFIG_EXTENSIONS, DOCKERFILE_NAMES, err_unsupported
from . import python_parser, ts_parser, config_parser


def _route(path: str):
    p = Path(path)
    ext = p.suffix.lower()
    name = p.name.lower()
    if ext in PY_EXTENSIONS:
        return python_parser
    if ext in TS_EXTENSIONS:
        return ts_parser
    if ext in CONFIG_EXTENSIONS or name in DOCKERFILE_NAMES or name.startswith("dockerfile."):
        return config_parser
    return None


def _try_lsp_first(path: str) -> bool:
    return _route(path) in (python_parser, ts_parser)


def structure(path: str) -> str:
    """Flat symbol name list. Cheapest orientation tool."""
    if _try_lsp_first(path):
        from .lsp.lsp_parser import structure as lsp_structure
        result = lsp_structure(path)
        if result:
            return result
    parser = _route(path)
    return parser.structure(path) if parser else err_unsupported(path)


def skeleton(path: str) -> str:
    """All signatures + first docstring. No bodies."""
    if _try_lsp_first(path):
        from .lsp.lsp_parser import skeleton as lsp_skeleton
        result = lsp_skeleton(path)
        if result:
            return result
    parser = _route(path)
    return parser.skeleton(path) if parser else err_unsupported(path)


def symbol_body(path: str, name: str) -> str:
    """Full source of one named symbol."""
    if _try_lsp_first(path):
        from .lsp.lsp_parser import symbol_body as lsp_symbol_body
        result = lsp_symbol_body(path, name)
        if result:
            return result
    parser = _route(path)
    return parser.symbol_body(path, name) if parser else err_unsupported(path)


def imports(path: str) -> str:
    """Import/require block only."""
    parser = _route(path)
    return parser.imports(path) if parser else err_unsupported(path)


def find_references(symbol: str, root_dir: str) -> str:
    """Returns file:line pairs where symbol appears. Skips node_modules and dot dirs."""
    if not os.path.isdir(root_dir):
        return f"Directory not found: {root_dir}"

    pattern = re.compile(r"\b" + re.escape(symbol) + r"\b")
    results: list[str] = []

    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [
            d for d in dirs
            if not d.startswith(".") and d != "node_modules" and d != "__pycache__" and d != "tests" and d != "notebooks"
        ]
        for fname in files:
            filepath = os.path.join(root, fname)
            try:
                with open(filepath, encoding="utf-8", errors="ignore") as fh:
                    for i, line in enumerate(fh, 1):
                        if pattern.search(line):
                            results.append(f"{filepath}:{i}")
            except OSError:
                pass

    return "\n".join(results) if results else "(no references found)"


def _open_workspace_files(client: object, root_dir: str, extensions: frozenset[str], language_id: str) -> None:
    """Open all matching files in workspace so LSP can index them."""
    skip_dirs = {"node_modules", "__pycache__", ".git", ".venv", "venv", "dist", "build"}
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
        for fname in files:
            if Path(fname).suffix.lower() in extensions:
                client.open_file(os.path.join(root, fname), language_id)  # type: ignore[attr-defined]


def lsp_references(symbol: str, path: str, root_dir: str) -> str:
    """Semantic references via LSP. Falls back to regex if LSP unavailable."""
    from .lsp.bridge import find_symbol_line, lsp_language_id, lsp_language_key
    from .lsp.manager import get_server
    from .lsp.client import uri_to_path

    pos = find_symbol_line(path, symbol)
    if pos is None:
        return find_references(symbol, root_dir)

    language_key = lsp_language_key(path)
    client = get_server(language_key, root_dir)
    if client is None:
        return find_references(symbol, root_dir)

    workspace_extensions = PY_EXTENSIONS if language_key == "python" else TS_EXTENSIONS
    _open_workspace_files(client, root_dir, workspace_extensions, lsp_language_id(path))
    refs = client.references(path, pos[0], pos[1])

    if not refs:
        return find_references(symbol, root_dir)

    results: list[str] = []
    for ref in refs:
        try:
            ref_path = uri_to_path(ref["uri"])
            line = ref["range"]["start"]["line"] + 1
            results.append(f"{ref_path}:{line}")
        except Exception:
            pass

    return "\n".join(results) if results else find_references(symbol, root_dir)


def lsp_hover(path: str, symbol: str, root_dir: str | None = None) -> str:
    """Type signature and docs for a symbol via LSP."""
    from .lsp.bridge import find_symbol_line, lsp_language_id, lsp_language_key
    from .lsp.manager import get_server

    pos = find_symbol_line(path, symbol)
    if pos is None:
        return f"Symbol '{symbol}' not found in {path}"

    effective_root = root_dir or str(Path(path).parent)
    language_key = lsp_language_key(path)
    client = get_server(language_key, effective_root)
    if client is None:
        lsp_server_name = "pylsp" if language_key == "python" else "typescript-language-server"
        return f"LSP unavailable. Install: {lsp_server_name}"

    client.open_file(path, lsp_language_id(path))
    result = client.hover(path, pos[0], pos[1])

    if not result:
        return f"No hover info for '{symbol}'"

    contents = result.get("contents", "")
    if isinstance(contents, dict):
        return contents.get("value", str(contents))
    if isinstance(contents, list):
        parts = []
        for c in contents:
            parts.append(c.get("value", c) if isinstance(c, dict) else str(c))
        return "\n".join(parts)
    return str(contents)
