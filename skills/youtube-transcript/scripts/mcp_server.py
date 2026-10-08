"""Entry point for the MCP server: python mcp_server.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ytx.mcp_server import main  # noqa: E402

if __name__ == "__main__":
    main()
