---
name: youtube-transcript
description: Get the transcript of a YouTube video from its link. Use when the user pastes a youtube.com / youtu.be link (watch, shorts, embed, live) and wants the transcript, a summary, notes, quotes, or answers about what the video says. Returns clean timestamped text with the caption source (human or auto-generated). No audio transcription; videos without captions return an error.
---

# youtube-transcript

Fetches captions with `youtube-transcript-api`, then `yt-dlp` if the first method fails. Both read YouTube's caption data without an API key or login.

**Setup:**
- **`PY`** is the Python in the tool venv: `~/.claude/tools/ytx-venv/Scripts/python.exe` on Windows, `~/.claude/tools/ytx-venv/bin/python` on macOS/Linux.
- If the venv is missing, ask the user, then run `python3 -m venv ~/.claude/tools/ytx-venv` (`py -3 -m venv` on Windows) and `PY -m pip install youtube-transcript-api yt-dlp`.
- **`SK`** is this skill's folder, `~/.claude/skills/youtube-transcript`.

## Use

```bash
PY SK/scripts/get_transcript.py "<url>" [--lang en,hi] [--out path.txt]
```

`--lang` is a priority list. Human captions beat auto captions inside the list. The default is `en`.

The command prints one JSON object. On success:

| Key | Meaning |
|---|---|
| `text` | Full transcript. Present only when `word_count` ≤ 6000. |
| `path` | The transcript file, always written (default `~/.claude/ytx-cache/<id>.<lang>.txt`). |
| `source` | `manual` (human-written, reliable) or `auto` (speech recognition: may misspell names, jargon, numbers). |
| `method`, `language`, `duration_min`, `word_count`, `title`, `channel` | Metadata. |

If `text` is absent, the video is long. Read `path` in parts with Read `offset`/`limit`. Do not load the whole file at once unless the task needs it.

The text has a short header, then paragraphs. Each paragraph starts with a `[mm:ss]` mark (about every 45 s).

## When you answer
- Say the source: tell the user if the transcript is `auto`, and flag any name or number you doubt.
- Cite times: quote the `[mm:ss]` mark for each claim so the user can check it in the video.
- Quote at most a short phrase; summarise the rest in your own words.

## Errors
On failure the JSON is `{"ok": false, "error": CODE, "detail": ...}` and the exit code is 1.

| `error` | Meaning | What to do |
|---|---|---|
| `bad_url` | Not a YouTube video link | Ask for a video link (playlists and channels are not supported) |
| `no_transcript` | No captions in that language, or captions are off | Read `detail` for the available languages and retry with `--lang`; otherwise tell the user. There is no audio fallback. |
| `private_or_unavailable` | Private, deleted, region-locked or age-restricted | Tell the user |
| `blocked` | YouTube refused the request (bot check, 429) | Wait and retry once. Do not hammer. If it persists, update the libraries: `PY -m pip install -U youtube-transcript-api yt-dlp` |
| `fetch_failed` | Network error or a YouTube change broke both methods | Retry once; then update the libraries; then report the `detail` |

## Optional: MCP server
`SK/scripts/mcp_server.py` exposes the same code as one tool, `get_transcript(url, lang)`. It needs the `mcp` package (`PY -m pip install mcp`). Register it only if the user asks:

```bash
claude mcp add youtube-transcript -- PY SK/scripts/mcp_server.py
```

## Notes
- This uses YouTube's unofficial caption access. It is meant for personal use, a few videos a day, from a home connection. Cloud servers are often blocked.
- YouTube changes break these libraries now and then. Updating them is the usual fix.
