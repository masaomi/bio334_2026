"""CLI entry point for bio334-teaching."""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="bio334-teaching",
        description="BIO334 Teaching Chain - Learn Python through population genetics",
    )
    subparsers = parser.add_subparsers(dest="command")

    # serve (default)
    serve_parser = subparsers.add_parser("serve", help="Start web GUI (default)")
    serve_parser.add_argument("--port", type=int, default=8334, help="Port (default: 8334)")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host (default: 127.0.0.1)")
    serve_parser.add_argument("--no-browser", action="store_true", help="Don't auto-open browser")
    serve_parser.add_argument(
        "--backend", choices=["auto", "api", "claude-code"], default="auto",
        help="Chat backend: 'api' (Anthropic API), 'claude-code' (local Claude CLI), 'auto' (default)"
    )

    # mcp
    mcp_parser = subparsers.add_parser("mcp", help="Run as MCP server (stdio)")
    mcp_parser.add_argument("--http", action="store_true", help="Use streamable HTTP transport")
    mcp_parser.add_argument("--port", type=int, default=8335, help="HTTP port (default: 8335)")

    # export (instructor only)
    export_parser = subparsers.add_parser("export", help="Export knowledge from kairos-chain")
    export_parser.add_argument("--kairos-dir", help="Path to .kairos directory")
    export_parser.add_argument("--output", help="Output directory")

    # version
    subparsers.add_parser("version", help="Show version")

    # Common options
    parser.add_argument("--api-key", help="Anthropic API key")
    parser.add_argument("--proxy", help="API proxy URL")
    parser.add_argument("--progress-dir", help="Progress save directory")

    args = parser.parse_args()

    # Default to serve if no command given
    if args.command is None:
        args.command = "serve"
        args.port = 8334
        args.host = "127.0.0.1"
        args.no_browser = False
        args.backend = "auto"

    if args.command == "version":
        from bio334_teaching import __version__
        print(f"bio334-teaching {__version__}")
        return

    if args.command == "export":
        from bio334_teaching.scripts.export_knowledge import export_from_kairos
        export_from_kairos(args.kairos_dir, args.output)
        return

    if args.command == "mcp":
        from bio334_teaching.interfaces.mcp.server import run_mcp
        run_mcp(http=args.http, port=args.port, api_key=args.api_key, proxy=args.proxy)
        return

    if args.command == "serve":
        from bio334_teaching.interfaces.web.startup import start_server
        start_server(
            host=args.host,
            port=args.port,
            open_browser=not args.no_browser,
            api_key=args.api_key,
            proxy=args.proxy,
            progress_dir=args.progress_dir,
            backend=args.backend,
        )
        return


if __name__ == "__main__":
    main()
