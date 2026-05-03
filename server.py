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


if __name__ == "__main__":
    mcp.run()
