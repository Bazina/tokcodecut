import argparse
import sys
from pathlib import Path

if __package__:
    from . import dispatcher
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tokcodecut import dispatcher


def main() -> None:
    """CLI entry point for tokcodecut."""
    parser = argparse.ArgumentParser(
        prog="tokcodecut",
        description="Token-optimized code lens — semantic access without reading whole files",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("structure", help="Flat symbol name list")
    p.add_argument("path")

    p = sub.add_parser("skeleton", help="All signatures + first docstring")
    p.add_argument("path")

    p = sub.add_parser("body", help="Full source of one symbol")
    p.add_argument("path")
    p.add_argument("name")

    p = sub.add_parser("imports", help="Import block only")
    p.add_argument("path")

    p = sub.add_parser("refs", help="Cross-file references to symbol (regex)")
    p.add_argument("symbol")
    p.add_argument("root_dir")

    p = sub.add_parser("lsp-refs", help="Semantic cross-file references via LSP (falls back to regex)")
    p.add_argument("symbol")
    p.add_argument("path", help="File where symbol is defined")
    p.add_argument("root_dir")

    p = sub.add_parser("lsp-hover", help="Type signature and docs via LSP")
    p.add_argument("path")
    p.add_argument("symbol")
    p.add_argument("--root-dir", default="", help="Workspace root (defaults to file's parent)")

    args = parser.parse_args()

    if args.command == "structure":
        print(dispatcher.structure(args.path))
    elif args.command == "skeleton":
        print(dispatcher.skeleton(args.path))
    elif args.command == "body":
        print(dispatcher.symbol_body(args.path, args.name))
    elif args.command == "imports":
        print(dispatcher.imports(args.path))
    elif args.command == "refs":
        print(dispatcher.find_references(args.symbol, args.root_dir))
    elif args.command == "lsp-refs":
        print(dispatcher.lsp_references(args.symbol, args.path, args.root_dir))
    elif args.command == "lsp-hover":
        print(dispatcher.lsp_hover(args.path, args.symbol, args.root_dir or None))


if __name__ == "__main__":
    main()
