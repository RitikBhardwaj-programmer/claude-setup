import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ytx import core  # noqa: E402
from ytx.core import Segment, TranscriptError  # noqa: E402

VID = "dQw4w9WgXcQ"


@pytest.mark.parametrize("url", [
    f"https://www.youtube.com/watch?v={VID}",
    f"https://youtube.com/watch?v={VID}&t=42s",
    f"https://www.youtube.com/watch?feature=share&v={VID}",
    f"https://youtu.be/{VID}",
    f"https://youtu.be/{VID}?si=abc&t=10",
    f"https://www.youtube.com/shorts/{VID}",
    f"https://www.youtube.com/embed/{VID}",
    f"https://www.youtube.com/live/{VID}?feature=share",
    f"https://m.youtube.com/watch?v={VID}",
    f"https://www.youtube.com/watch?v={VID}&list=PLabc&index=3",
    f"youtube.com/watch?v={VID}",
    VID,
])
def test_parse_ok(url):
    assert core.parse_video_id(url) == VID


@pytest.mark.parametrize("url", [
    "", "hello", "https://example.com/watch?v=" + VID,
    "https://www.youtube.com/", "https://www.youtube.com/playlist?list=PLabc",
    "https://www.youtube.com/watch?v=short",
])
def test_parse_bad(url):
    with pytest.raises(TranscriptError) as ei:
        core.parse_video_id(url)
    assert ei.value.code == "bad_url"


def test_dedupe_exact_repeat_and_rolling():
    segs = [Segment(0, "hello"), Segment(1, "hello"), Segment(2, "hello world"),
            Segment(3, "hello world"), Segment(4, "next line")]
    assert [s.text for s in core.dedupe(segs)] == ["hello world", "next line"]


def test_dedupe_keeps_start_of_first_line_and_whitespace():
    segs = [Segment(5, "a  b\n"), Segment(6, "a b c")]
    out = core.dedupe(segs)
    assert [(s.start, s.text) for s in out] == [(5, "a b c")]


def test_format_marks_every_45s():
    segs = [Segment(t, f"w{t}") for t in (0, 10, 44, 45, 50, 95)]
    body = core.format_body(segs)
    assert body.split("\n\n") == ["[00:00] w0 w10 w44", "[00:45] w45 w50", "[01:35] w95"]


def test_format_hours():
    body = core.format_body([Segment(0, "a"), Segment(3700, "b")])
    assert "[0:00:00]" in body and "[1:01:40]" in body


def test_format_empty():
    assert core.format_body([]) == ""


def test_parse_json3():
    data = {"events": [{"tStartMs": 1500, "segs": [{"utf8": "Hel"}, {"utf8": "lo\n"}]},
                       {"tStartMs": 2000}, {"tStartMs": 3000, "segs": [{"utf8": "\n"}]}]}
    assert [(s.start, s.text) for s in core.parse_json3(data)] == [(1.5, "Hello")]


def test_fallback_used_when_api_blocked(monkeypatch):
    def boom(*a):
        raise RuntimeError("RequestBlocked")
    ok = core.Fetched(VID, [Segment(0, "x")], "en", "en", "auto", "yt-dlp")
    monkeypatch.setattr(core, "_fetch_api", boom)
    monkeypatch.setattr(core, "_fetch_ytdlp", lambda *a: ok)
    assert core.fetch_segments(VID, ["en"]).method == "yt-dlp"


def test_final_error_skips_fallback(monkeypatch):
    def none(*a):
        raise TranscriptError("no_transcript", "x")
    called = []
    monkeypatch.setattr(core, "_fetch_api", none)
    monkeypatch.setattr(core, "_fetch_ytdlp", lambda *a: called.append(1))
    with pytest.raises(TranscriptError) as ei:
        core.fetch_segments(VID, ["en"])
    assert ei.value.code == "no_transcript" and not called
