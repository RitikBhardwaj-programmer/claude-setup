"""Core logic: parse a URL, fetch caption segments (two methods), clean and format them.

No other module holds fetch logic, so the CLI and the MCP server share exactly this code.
"""
import json
import re
import tempfile
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

MARK_EVERY_S = 45  # one [mm:ss] mark per paragraph, at least this many seconds apart
INLINE_WORD_LIMIT = 6000  # longer transcripts are returned as a file path only
CACHE_DIR = Path.home() / ".claude" / "ytx-cache"

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_PATH_ID_RE = re.compile(r"^/(?:shorts|embed|live|v|e)/([A-Za-z0-9_-]{11})(?:[/?]|$)")
_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com",
          "youtube-nocookie.com", "www.youtube-nocookie.com"}


class TranscriptError(Exception):
    """A failure with a stable machine-readable `code`."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


@dataclass
class Segment:
    start: float
    text: str


@dataclass
class Fetched:
    video_id: str
    segments: list
    language: str
    language_code: str
    source: str  # "manual" or "auto"
    method: str  # "youtube-transcript-api" or "yt-dlp"
    available: list = field(default_factory=list)


def parse_video_id(url: str) -> str:
    """Return the 11-character video ID from a YouTube URL (or a bare ID). Raise bad_url if none."""
    s = (url or "").strip()
    if _ID_RE.match(s):
        return s
    if "://" not in s:
        s = "https://" + s
    p = urllib.parse.urlparse(s)
    host = (p.hostname or "").lower()
    if host in ("youtu.be", "www.youtu.be"):
        vid = p.path.lstrip("/").split("/")[0]
    elif host in _HOSTS:
        m = _PATH_ID_RE.match(p.path)
        vid = m.group(1) if m else urllib.parse.parse_qs(p.query).get("v", [""])[0]
    else:
        raise TranscriptError("bad_url", f"not a YouTube host: {host or url!r}")
    if not _ID_RE.match(vid):
        raise TranscriptError("bad_url", f"no video ID found in {url!r}")
    return vid


# ---------- fetch method 1: youtube-transcript-api ----------

def _fetch_api(video_id: str, langs: list) -> Fetched:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api import _errors as e

    api = YouTubeTranscriptApi()
    try:
        tlist = api.list(video_id)
        available = [t.language_code + ("*" if t.is_generated else "") for t in tlist]
        ft = tlist.find_transcript(langs).fetch()
    except e.NoTranscriptFound as ex:
        raise TranscriptError("no_transcript", f"none in {langs}; available: {available}") from ex
    except e.TranscriptsDisabled as ex:
        raise TranscriptError("no_transcript", "captions are disabled for this video") from ex
    except (e.VideoUnavailable, e.VideoUnplayable, e.InvalidVideoId, e.AgeRestricted) as ex:
        raise TranscriptError("private_or_unavailable", type(ex).__name__) from ex
    segs = [Segment(s.start, s.text) for s in ft.snippets]
    return Fetched(video_id, segs, ft.language, ft.language_code,
                   "auto" if ft.is_generated else "manual", "youtube-transcript-api", available)


# ---------- fetch method 2: yt-dlp ----------

class _SilentLogger:
    """Keep yt-dlp quiet: stdout must carry only the final JSON."""
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass


def parse_json3(data: dict) -> list:
    """Turn YouTube json3 caption data into Segments."""
    out = []
    for ev in data.get("events", []):
        segs = ev.get("segs")
        if not segs:
            continue
        text = "".join(s.get("utf8", "") for s in segs).replace("\n", " ").strip()
        if text:
            out.append(Segment(ev.get("tStartMs", 0) / 1000.0, text))
    return out


def _fetch_ytdlp(video_id: str, langs: list) -> Fetched:
    import yt_dlp
    from yt_dlp.utils import DownloadError

    url = f"https://www.youtube.com/watch?v={video_id}"
    with tempfile.TemporaryDirectory() as tmp:
        opts = {"skip_download": True, "writesubtitles": True, "writeautomaticsub": True,
                "subtitleslangs": langs, "subtitlesformat": "json3", "quiet": True,
                "no_warnings": True, "noprogress": True, "logger": _SilentLogger(),
                "socket_timeout": 30, "retries": 3, "outtmpl": str(Path(tmp) / "%(id)s")}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
        except DownloadError as ex:
            msg = str(ex).lower()
            if any(k in msg for k in ("private", "unavailable", "removed", "terminated", "age")):
                raise TranscriptError("private_or_unavailable", str(ex)[:200]) from ex
            if any(k in msg for k in ("429", "bot", "sign in", "403")):
                raise TranscriptError("blocked", str(ex)[:200]) from ex
            raise TranscriptError("fetch_failed", str(ex)[:200]) from ex
        manual = info.get("subtitles") or {}
        auto = info.get("automatic_captions") or {}
        for lang in langs:  # manual tracks beat auto tracks, in language-priority order
            for source, table in (("manual", manual), ("auto", auto)):
                f = Path(tmp) / f"{video_id}.{lang}.json3"
                if lang in table and f.exists():
                    segs = parse_json3(json.loads(f.read_text(encoding="utf-8")))
                    return Fetched(video_id, segs, lang, lang, source, "yt-dlp", sorted(manual))
        raise TranscriptError("no_transcript", f"none in {langs} (yt-dlp)")


# Errors that mean "this video has no usable transcript" are final; anything else tries the next method.
_FINAL = {"no_transcript", "private_or_unavailable", "bad_url"}


def fetch_segments(video_id: str, langs: list) -> Fetched:
    """Try youtube-transcript-api, then yt-dlp. Final errors are not retried with the second method."""
    try:
        return _fetch_api(video_id, langs)
    except TranscriptError as ex:
        first = ex
    except Exception as ex:  # blocked, PoToken, parse errors, network: anything unexpected
        first = TranscriptError("blocked" if "block" in type(ex).__name__.lower() else "fetch_failed",
                                f"{type(ex).__name__}: {str(ex)[:150]}")
    if first.code in _FINAL:
        raise first
    try:
        return _fetch_ytdlp(video_id, langs)
    except TranscriptError as second:
        raise TranscriptError(second.code, f"api: {first.detail} | yt-dlp: {second.detail}") from second
    except Exception as ex:
        raise TranscriptError("fetch_failed", f"api: {first.detail} | yt-dlp: {type(ex).__name__}: {str(ex)[:150]}") from ex


# ---------- clean and format ----------

def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", t.replace("​", "")).strip()


def dedupe(segments: list) -> list:
    """Drop repeated lines and merge rolling auto-captions where each line extends the previous one."""
    out = []
    for s in segments:
        text = _norm(s.text)
        if not text:
            continue
        if out:
            prev = out[-1].text
            if text == prev or prev.endswith(text):
                continue
            if text.startswith(prev):  # rolling caption: new line contains the old one
                out[-1] = Segment(out[-1].start, text)
                continue
        out.append(Segment(s.start, text))
    return out


def _stamp(sec: float, hours: bool) -> str:
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"[{h}:{m:02d}:{s:02d}]" if hours else f"[{m:02d}:{s:02d}]"


def format_body(segments: list, mark_every: int = MARK_EVERY_S) -> str:
    """Paragraphs of clean text, each starting with a [mm:ss] mark at least `mark_every` seconds apart."""
    segs = dedupe(segments)
    if not segs:
        return ""
    hours = segs[-1].start >= 3600
    paras, cur, mark_t = [], [], None
    for s in segs:
        if mark_t is None or s.start - mark_t >= mark_every:
            if cur:
                paras.append(" ".join(cur))
            cur = [_stamp(s.start, hours)]
            mark_t = s.start
        cur.append(s.text)
    paras.append(" ".join(cur))
    return "\n\n".join(paras)


def video_meta(video_id: str) -> dict:
    """Best-effort title and channel through the public oEmbed endpoint. Empty dict on any failure."""
    url = ("https://www.youtube.com/oembed?format=json&url="
           + urllib.parse.quote(f"https://www.youtube.com/watch?v={video_id}", safe=""))
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            d = json.load(r)
        return {"title": d.get("title", ""), "channel": d.get("author_name", "")}
    except Exception:
        return {}


def run(url: str, langs: list = None, out: str = None) -> dict:
    """`build`, but a failure becomes {"ok": False, "error": code, "detail": ...}. Used by the CLI and MCP."""
    try:
        return build(url, langs, out)
    except TranscriptError as ex:
        return {"ok": False, "error": ex.code, "detail": ex.detail}


def build(url: str, langs: list = None, out: str = None) -> dict:
    """Full pipeline. Return a result dict (see SKILL.md); raise TranscriptError on failure."""
    langs = langs or ["en"]
    vid = parse_video_id(url)
    f = fetch_segments(vid, langs)
    body = format_body(f.segments)
    if not body:
        raise TranscriptError("no_transcript", "the caption track is empty")
    segs = dedupe(f.segments)
    meta = video_meta(vid)
    words = len(body.split())
    duration = int(segs[-1].start) if segs else 0
    header = (f"Title: {meta.get('title', '?')}\nChannel: {meta.get('channel', '?')}\n"
              f"URL: https://www.youtube.com/watch?v={vid}\n"
              f"Language: {f.language_code} | Source: {f.source}-captions | Length: ~{duration // 60} min, {words} words\n"
              f"Note: {'auto-generated captions can misspell names and jargon' if f.source == 'auto' else 'human-written captions'}.\n")
    text = header + "\n" + body + "\n"
    path = Path(out) if out else CACHE_DIR / f"{vid}.{f.language_code}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    res = {"ok": True, "video_id": vid, "title": meta.get("title", ""), "channel": meta.get("channel", ""),
           "language": f.language_code, "source": f.source, "method": f.method,
           "duration_min": duration // 60, "word_count": words, "path": str(path)}
    if words <= INLINE_WORD_LIMIT:
        res["text"] = text
    else:
        res["note"] = "Long transcript: read the file in parts (Read with offset/limit)."
    return res
