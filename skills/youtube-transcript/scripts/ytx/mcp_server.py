"""MCP server (stdio) exposing one tool, `get_transcript`, over the same core as the CLI.

Run with the tool venv: python scripts/mcp_server.py   (needs the `mcp` package, version 2.x)
"""
import json

from mcp.server.mcpserver import MCPServer

from .core import run

server = MCPServer("youtube-transcript")


@server.tool()
def get_transcript(url: str, lang: str = "en") -> str:
    """Get a YouTube video's transcript from its link.

    Returns JSON. On success: `text` (clean paragraphs with [mm:ss] marks; present only when the video
    has 6000 words or fewer), `path` (the saved transcript file; read it in parts for long videos),
    `source` ("manual" = human captions, "auto" = speech recognition that can misspell names), plus
    title, channel, language, duration_min and word_count. On failure: {"ok": false, "error": code,
    "detail": ...} with code bad_url, no_transcript, private_or_unavailable, blocked or fetch_failed.
    `lang` is a comma-separated priority list such as "en,hi".
    """
    return json.dumps(run(url, [x.strip() for x in lang.split(",") if x.strip()]), ensure_ascii=False)


def main() -> None:
    server.run("stdio")
