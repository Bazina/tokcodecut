from pathlib import Path

PY_EXTENSIONS = frozenset({".py"})
TS_EXTENSIONS = frozenset({".ts", ".tsx", ".js", ".jsx", ".svelte"})
CONFIG_EXTENSIONS = frozenset({".json", ".yml", ".yaml", ".dockerfile"})
DOCKERFILE_NAMES = frozenset({"dockerfile"})
ALL_SUPPORTED = PY_EXTENSIONS | TS_EXTENSIONS | CONFIG_EXTENSIONS | frozenset({"Dockerfile"})


def err_not_found(path: str) -> str:
    return f"File not found: {path}"


def err_symbol_not_found(name: str, path: str) -> str:
    return f"Symbol '{name}' not found in {path}"


def err_unsupported(path: str) -> str:
    ext = Path(path).suffix
    supported = " ".join(sorted(ALL_SUPPORTED))
    return f"Unsupported extension '{ext}' in {path}. Supported: {supported} Dockerfile"


def err_parse(path: str, message: str) -> str:
    return f"Parse error in {path}: {message}"


def err_no_node() -> str:
    return "Node.js required for TypeScript files. Install Node.js."
