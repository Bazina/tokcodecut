# tokcodecut

Token-optimized MCP server that gives Claude surgical read access to source files. Instead of reading entire files, Claude calls semantic tools to get only the pieces it needs — structure, signatures, single symbols, imports, or cross-file references.

**Cuts 70–95% of tokens** on typical code navigation tasks.

---

## Why

When Claude reads a 500-line file to find one function, it burns thousands of tokens on irrelevant code. `tokcodecut` exposes the file's AST as tools — Claude gets exactly what it needs, nothing more.

---

## Tools

| Tool | Returns | Token cost |
|------|---------|-----------|
| `structure(path)` | Flat symbol name list | Cheapest — use first |
| `skeleton(path)` | All signatures + first docstring line | Low |
| `symbol_body(path, name)` | Full source of one symbol | Medium — only when needed |
| `imports(path)` | Import/require block only | Low |
| `find_references(symbol, root_dir)` | `file:line` pairs across entire codebase | Low |

### Example outputs

**`structure`**
```
MyClass
  __init__
  process_data
  _validate
fetch_records
build_index
```

**`skeleton`**
```python
class MyClass(Base):
    """Handles record processing."""
    def __init__(self, client: KintoneClient) -> None: ...
    async def process_data(self, rows: list[Row]) -> Result:
        """Process and deduplicate rows."""

async def fetch_records(app_id: str) -> list[dict]:
    """Fetch all records from Kintone app."""
```

**`find_references`**
```
src/index.ts:12
packages/client/src/api.ts:4
```

---

## Supported Languages

| Extension | Parser |
|-----------|--------|
| `.py` | Python `ast` stdlib — zero dependencies |
| `.ts` `.tsx` `.js` `.jsx` | `ts-morph` via Node subprocess |
| `.svelte` | `<script>` block extracted → `ts-morph` |

---

## Install

**Requirements:** Python 3.11+, Node.js, `uv`

```bash
git clone https://github.com/Bazina/tokcodecut
cd tokcodecut
uv sync
cd node && npm install
```

---

## MCP Server (Claude Code)

Register as a global MCP server:

```bash
claude mcp add tokcodecut --scope user -- uv run --directory /path/to/tokcodecut python server.py
```

Or add to `~/.claude.json` manually:

```json
{
  "mcpServers": {
    "tokcodecut": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/tokcodecut", "python", "server.py"]
    }
  }
}
```

Then add to `~/.claude/CLAUDE.md` so Claude uses it automatically:

```markdown
## tokcodecut
Prefer tokcodecut tools over Read for source files:
- `structure(path)` first — orientation, cheapest tokens
- `skeleton(path)` — understand API surface before editing
- `symbol_body(path, name)` — only when full implementation needed
- `find_references(symbol, root_dir)` — cross-file usage
- Fall back to Read only when tokcodecut fails or file is config/data (JSON, YAML, TOML, etc.)
```

---

## CLI

Same parser logic as the MCP server — no server needed for testing.

```bash
# Install globally
uv tool install .

# Or run directly
uv run tokcodecut <command>
```

```bash
tokcodecut structure path/to/file.py
tokcodecut skeleton path/to/file.ts
tokcodecut body path/to/file.py MyClass
tokcodecut imports path/to/file.svelte
tokcodecut refs MyClass /path/to/project/root
```

---

## Error Handling

All tools return plain strings — no exceptions propagate to Claude.

| Condition | Response |
|-----------|----------|
| File not found | `File not found: <path>` |
| Symbol not found | `Symbol '<name>' not found in <path>` |
| Unsupported extension | `Unsupported extension '.<ext>' in <path>. Supported: .js .jsx .py .svelte .ts .tsx` |
| Node.js not available | `Node.js required for TypeScript files. Install Node.js.` |
| Parse error | `Parse error in <path>: <message>` |

---

## Architecture

```
Claude calls MCP tool
  → server.py (FastMCP, stdio transport)
    → dispatcher.py (routes by file extension)
      → python_parser.py  (.py files, stdlib ast)
        OR ts_parser.py   (.ts .tsx .js .jsx .svelte)
          → node/ts_lens.mjs (ts-morph subprocess)
```

```
tokcodecut/
├── tokcodecut/
│   ├── dispatcher.py     # routes by extension
│   ├── python_parser.py  # ast-based parser
│   ├── ts_parser.py      # node subprocess wrapper
│   ├── models.py         # error helpers + extension sets
│   └── cli.py            # CLI entry point
├── node/
│   └── ts_lens.mjs       # ts-morph script → JSON stdout
├── server.py             # FastMCP stdio server
└── pyproject.toml
```

---

## Development

```bash
# Run tests
uv run pytest

# Test CLI directly
uv run tokcodecut structure tokcodecut/dispatcher.py
uv run tokcodecut skeleton tokcodecut/python_parser.py
uv run tokcodecut body tokcodecut/python_parser.py structure
uv run tokcodecut refs structure /path/to/tokcodecut
```

---

## License

MIT
