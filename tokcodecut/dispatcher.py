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


def structure(path: str) -> str:
    """Flat symbol name list. Cheapest orientation tool."""
    parser = _route(path)
    return parser.structure(path) if parser else err_unsupported(path)


def skeleton(path: str) -> str:
    """All signatures + first docstring. No bodies."""
    parser = _route(path)
    return parser.skeleton(path) if parser else err_unsupported(path)


def symbol_body(path: str, name: str) -> str:
    """Full source of one named symbol."""
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
