from mcp.server.fastmcp import FastMCP
from tokcodecut import dispatcher

mcp = FastMCP("tokcodecut")


@mcp.tool()
def structure(path: str) -> str:
    """Flat list of symbol names in file. Cheapest token cost — use first for orientation."""
    return dispatcher.structure(path)


@mcp.tool()
def skeleton(path: str) -> str:
    """All signatures + first docstring line. No function bodies."""
    return dispatcher.skeleton(path)


@mcp.tool()
def symbol_body(path: str, name: str) -> str:
    """Full source of one named symbol. Use only when full implementation is needed."""
    return dispatcher.symbol_body(path, name)


@mcp.tool()
def imports(path: str) -> str:
    """Import/require block only. Nothing else."""
    return dispatcher.imports(path)


@mcp.tool()
def find_references(symbol: str, root_dir: str) -> str:
    """Returns file:line pairs where symbol is used across root_dir."""
    return dispatcher.find_references(symbol, root_dir)


@mcp.tool()
def lsp_references(symbol: str, path: str, root_dir: str) -> str:
    """Semantic references via LSP — accurate cross-file symbol usage, no false positives. Falls back to regex if LSP unavailable."""
    return dispatcher.lsp_references(symbol, path, root_dir)


@mcp.tool()
def lsp_hover(path: str, symbol: str, root_dir: str = "") -> str:
    """Type signature and docs for a symbol via LSP. No need to read the full file."""
    return dispatcher.lsp_hover(path, symbol, root_dir or None)


if __name__ == "__main__":
    mcp.run()
