import shutil
from .client import LspClient

_servers: dict[tuple[str, str], LspClient] = {}

_LANG_CMDS: dict[str, list[list[str]]] = {
    "python": [["pylsp"], ["pyright-langserver", "--stdio"]],
    "typescript": [["typescript-language-server", "--stdio"]],
    "javascript": [["typescript-language-server", "--stdio"]],
}


def _find_cmd(lang: str) -> list[str] | None:
    for candidate in _LANG_CMDS.get(lang, []):
        if shutil.which(candidate[0]):
            return candidate
    return None


def get_server(lang: str, root_dir: str) -> LspClient | None:
    key = (lang, root_dir)
    client = _servers.get(key)
    if client and client.is_alive():
        return client

    cmd = _find_cmd(lang)
    if cmd is None:
        return None

    try:
        client = LspClient(cmd, root_dir)
        _servers[key] = client
        return client
    except Exception:
        return None


def shutdown_all() -> None:
    for client in _servers.values():
        client.shutdown()
    _servers.clear()
