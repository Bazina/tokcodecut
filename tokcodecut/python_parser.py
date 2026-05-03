import ast
from pathlib import Path
from .models import err_not_found, err_parse, err_symbol_not_found


def _read(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return None


def _parse(source: str, path: str) -> ast.Module | str:
    try:
        return ast.parse(source)
    except SyntaxError as e:
        return err_parse(path, str(e))


def _first_docstring(node: ast.AST) -> str | None:
    if (
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    ):
        return node.body[0].value.value.split("\n")[0].strip()
    return None


def _func_sig(node: ast.FunctionDef | ast.AsyncFunctionDef, indent: str = "") -> str:
    prefix = "async def " if isinstance(node, ast.AsyncFunctionDef) else "def "
    args = ast.unparse(node.args)
    ret = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    return f"{indent}{prefix}{node.name}({args}){ret}: ..."


def structure(path: str) -> str:
    """Returns flat indented list of symbol names only."""
    source = _read(path)
    if source is None:
        return err_not_found(path)
    result = _parse(source, path)
    if isinstance(result, str):
        return result
    tree: ast.Module = result

    lines: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            lines.append(node.name)
        elif isinstance(node, ast.ClassDef):
            lines.append(node.name)
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    lines.append(f"  {child.name}")
    return "\n".join(lines) if lines else "(no symbols found)"


def skeleton(path: str) -> str:
    """Returns all signatures + first docstring line, no function bodies."""
    source = _read(path)
    if source is None:
        return err_not_found(path)
    result = _parse(source, path)
    if isinstance(result, str):
        return result
    tree: ast.Module = result

    parts: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            parts.append(_func_sig(node))
            doc = _first_docstring(node)
            if doc:
                parts.append(f'    """{doc}"""')
        elif isinstance(node, ast.ClassDef):
            bases = [ast.unparse(b) for b in node.bases]
            header = f"class {node.name}({', '.join(bases)}):" if bases else f"class {node.name}:"
            parts.append(header)
            doc = _first_docstring(node)
            if doc:
                parts.append(f'    """{doc}"""')
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    parts.append(_func_sig(child, indent="    "))
                    child_doc = _first_docstring(child)
                    if child_doc:
                        parts.append(f'        """{child_doc}"""')
            parts.append("")
    return "\n".join(parts) if parts else "(no symbols found)"


def symbol_body(path: str, name: str) -> str:
    """Returns full source of one named symbol."""
    source = _read(path)
    if source is None:
        return err_not_found(path)
    result = _parse(source, path)
    if isinstance(result, str):
        return result
    tree: ast.Module = result

    source_lines = source.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == name:
                return "\n".join(source_lines[node.lineno - 1 : node.end_lineno])
    return err_symbol_not_found(name, path)


def imports(path: str) -> str:
    """Returns import/from-import block only."""
    source = _read(path)
    if source is None:
        return err_not_found(path)
    result = _parse(source, path)
    if isinstance(result, str):
        return result
    tree: ast.Module = result

    source_lines = source.splitlines()
    lines: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            lines.extend(source_lines[node.lineno - 1 : node.end_lineno])
    return "\n".join(lines) if lines else "(no imports)"
