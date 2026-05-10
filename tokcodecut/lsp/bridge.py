import ast
from pathlib import Path


def find_symbol_line(path: str, symbol: str) -> tuple[int, int] | None:
    """Returns (line, col) 0-indexed for symbol definition in file."""
    file_extension = Path(path).suffix.lower()
    if file_extension == ".py":
        return _python_symbol_line(path, symbol)
    return None


def _python_symbol_line(path: str, symbol: str) -> tuple[int, int] | None:
    try:
        source = Path(path).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=path)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name == symbol:
                    if isinstance(node, ast.AsyncFunctionDef):
                        name_col = node.col_offset + len("async def ")
                    elif isinstance(node, ast.FunctionDef):
                        name_col = node.col_offset + len("def ")
                    else:
                        name_col = node.col_offset + len("class ")
                    return (node.lineno - 1, name_col)
    except Exception:
        pass
    return None


def lsp_language_id(path: str) -> str:
    """Maps file path to LSP languageId string for textDocument/didOpen."""
    file_extension = Path(path).suffix.lower()
    mapping = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescriptreact",
        ".js": "javascript",
        ".jsx": "javascriptreact",
    }
    return mapping.get(file_extension, "plaintext")


def lsp_language_key(path: str) -> str:
    """Maps file path to language server process key (python or typescript)."""
    file_extension = Path(path).suffix.lower()
    if file_extension == ".py":
        return "python"
    if file_extension in {".ts", ".tsx", ".js", ".jsx"}:
        return "typescript"
    return "unknown"
