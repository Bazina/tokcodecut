import json
import subprocess
import threading
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname


def path_to_uri(path: str) -> str:
    return Path(path).resolve().as_uri()


def uri_to_path(uri: str) -> str:
    return url2pathname(urlparse(uri).path)


class LspClient:
    """Synchronous JSON-RPC stdio client for LSP servers."""

    def __init__(self, cmd: list[str], root_dir: str):
        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        self._next_id = 1
        self._id_lock = threading.Lock()
        self._results: dict[int, dict] = {}
        self._events: dict[int, threading.Event] = {}
        self._write_lock = threading.Lock()
        self._opened_files: set[str] = set()

        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()

        self._initialize(root_dir)

    def _write(self, msg: dict) -> None:
        body = json.dumps(msg).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode()
        with self._write_lock:
            assert self._proc.stdin is not None
            self._proc.stdin.write(header + body)
            self._proc.stdin.flush()

    def _read_loop(self) -> None:
        try:
            assert self._proc.stdout is not None
            while self._proc.poll() is None:
                content_length = 0
                while True:
                    raw = self._proc.stdout.readline()
                    if not raw:
                        return
                    line = raw.decode("utf-8", errors="replace").strip()
                    if not line:
                        break
                    if line.lower().startswith("content-length:"):
                        content_length = int(line.split(":", 1)[1].strip())

                if content_length <= 0:
                    continue

                body = b""
                while len(body) < content_length:
                    chunk = self._proc.stdout.read(content_length - len(body))
                    if not chunk:
                        return
                    body += chunk

                msg = json.loads(body.decode("utf-8"))
                msg_id = msg.get("id")
                if msg_id is not None and msg_id in self._events:
                    self._results[msg_id] = msg
                    self._events[msg_id].set()
        except Exception:
            pass

    def request(self, method: str, params: dict, timeout: float = 15.0) -> object:
        with self._id_lock:
            msg_id = self._next_id
            self._next_id += 1

        event = threading.Event()
        self._events[msg_id] = event
        self._write({"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params})

        if not event.wait(timeout):
            self._events.pop(msg_id, None)
            return None

        self._events.pop(msg_id, None)
        msg = self._results.pop(msg_id, {})
        if "error" in msg:
            return None
        return msg.get("result")

    def notify(self, method: str, params: dict) -> None:
        self._write({"jsonrpc": "2.0", "method": method, "params": params})

    def _initialize(self, root_dir: str) -> None:
        root_uri = path_to_uri(root_dir)
        self.request("initialize", {
            "processId": None,
            "rootUri": root_uri,
            "capabilities": {
                "textDocument": {
                    "references": {"dynamicRegistration": False},
                    "hover": {
                        "dynamicRegistration": False,
                        "contentFormat": ["plaintext", "markdown"],
                    },
                }
            },
            "workspaceFolders": [{"uri": root_uri, "name": Path(root_dir).name}],
        }, timeout=30.0)
        self.notify("initialized", {})

    def open_file(self, path: str, lang_id: str) -> None:
        uri = path_to_uri(path)
        if uri in self._opened_files:
            return
        self._opened_files.add(uri)
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError:
            return
        self.notify("textDocument/didOpen", {
            "textDocument": {"uri": uri, "languageId": lang_id, "version": 1, "text": text}
        })

    def document_symbols(self, path: str) -> list[dict] | None:
        return self.request("textDocument/documentSymbol", {  # type: ignore[return-value]
            "textDocument": {"uri": path_to_uri(path)},
        })

    def references(self, path: str, line: int, char: int) -> list[dict] | None:
        return self.request("textDocument/references", {  # type: ignore[return-value]
            "textDocument": {"uri": path_to_uri(path)},
            "position": {"line": line, "character": char},
            "context": {"includeDeclaration": True},
        })

    def hover(self, path: str, line: int, char: int) -> dict | None:
        return self.request("textDocument/hover", {  # type: ignore[return-value]
            "textDocument": {"uri": path_to_uri(path)},
            "position": {"line": line, "character": char},
        })

    def is_alive(self) -> bool:
        return self._proc.poll() is None

    def shutdown(self) -> None:
        try:
            self.request("shutdown", {}, timeout=5.0)
            self.notify("exit", {})
        except Exception:
            pass
        try:
            self._proc.terminate()
        except Exception:
            pass
