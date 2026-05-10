from pathlib import Path
from .bridge import lsp_language_id, lsp_language_key
from .manager import get_server

SYMBOL_KIND_LABEL: dict[int, str] = {
    5: "Class",
    6: "Method",
    9: "Constructor",
    10: "Enum",
    11: "Interface",
    12: "Function",
    14: "Constant",
    23: "Struct",
    26: "TypeParameter",
}

_SKELETON_SKIP_KINDS = {13}  # Variable — noise in skeleton (params, local vars)


def _get_symbols(path: str) -> list[dict] | None:
    language_key = lsp_language_key(path)
    if language_key == "unknown":
        return None
    root_dir = str(Path(path).parent)
    client = get_server(language_key, root_dir)
    if client is None:
        return None
    client.open_file(path, lsp_language_id(path))
    symbols = client.document_symbols(path)
    return symbols if symbols else None


def _top_level(symbols: list[dict]) -> list[dict]:
    return [s for s in symbols if not s.get("containerName")]


def _children_of(symbols: list[dict], parent_name: str) -> list[dict]:
    return [s for s in symbols if s.get("containerName") == parent_name]


def _source_lines(path: str) -> list[str]:
    try:
        return Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []


def _extract_range(source_lines: list[str], location: dict) -> str:
    start = location["range"]["start"]["line"]
    end = location["range"]["end"]["line"] + 1
    return "\n".join(source_lines[start:end])


def _signature_line(source_lines: list[str], location: dict) -> str:
    start = location["range"]["start"]["line"]
    return source_lines[start] if start < len(source_lines) else ""


def _docstring_line(source_lines: list[str], location: dict) -> str | None:
    start = location["range"]["start"]["line"]
    if start + 1 >= len(source_lines):
        return None
    next_line = source_lines[start + 1]
    stripped = next_line.strip()
    for quote in ('"""', "'''"):
        if stripped.startswith(quote):
            doc = stripped.removeprefix(quote)
            if doc.endswith(quote):
                doc = doc.removesuffix(quote).strip()
            if doc:
                indent = len(next_line) - len(next_line.lstrip())
                return " " * indent + f'"""{doc}"""'
    return None


_CLASS_KINDS = {5, 10, 11, 23}  # Class, Enum, Interface, Struct — have meaningful children
_MEMBER_KINDS = {6, 9, 12, 14}  # Method, Constructor, Function, Constant — show as children


def structure(path: str) -> str:
    """Symbol names with kind labels via LSP."""
    symbols = _get_symbols(path)
    if symbols is None:
        return ""

    lines: list[str] = []
    top_level = _top_level(symbols)
    for symbol in top_level:
        kind_label = SYMBOL_KIND_LABEL.get(symbol["kind"], "")
        prefix = f"[{kind_label}] " if kind_label else ""
        lines.append(f"{prefix}{symbol['name']}")
        if symbol["kind"] in _CLASS_KINDS:
            for child in _children_of(symbols, symbol["name"]):
                if child["kind"] not in _MEMBER_KINDS:
                    continue
                child_label = SYMBOL_KIND_LABEL.get(child["kind"], "")
                child_prefix = f"[{child_label}] " if child_label else ""
                lines.append(f"  {child_prefix}{child['name']}")

    return "\n".join(lines) if lines else "(no symbols found)"


def skeleton(path: str) -> str:
    """Signatures + first docstring line via LSP ranges."""
    symbols = _get_symbols(path)
    if symbols is None:
        return ""

    source_lines = _source_lines(path)
    if not source_lines:
        return ""

    parts: list[str] = []
    top_level = _top_level(symbols)
    for symbol in top_level:
        if symbol["kind"] in _SKELETON_SKIP_KINDS:
            continue
        sig = _signature_line(source_lines, symbol["location"])
        parts.append(sig)
        doc = _docstring_line(source_lines, symbol["location"])
        if doc:
            parts.append(doc)

        if symbol["kind"] in _CLASS_KINDS:
            for child in _children_of(symbols, symbol["name"]):
                if child["kind"] in _SKELETON_SKIP_KINDS:
                    continue
                child_sig = _signature_line(source_lines, child["location"])
                parts.append(child_sig)
                child_doc = _docstring_line(source_lines, child["location"])
                if child_doc:
                    parts.append(child_doc)

        parts.append("")

    return "\n".join(parts).rstrip() if parts else "(no symbols found)"


def symbol_body(path: str, name: str) -> str:
    """Full source of one named symbol via LSP ranges."""
    symbols = _get_symbols(path)
    if symbols is None:
        return ""

    source_lines = _source_lines(path)
    for symbol in symbols:
        if symbol["name"] == name:
            return _extract_range(source_lines, symbol["location"])
    return ""
