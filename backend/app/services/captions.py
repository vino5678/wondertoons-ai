"""Caption engine: build cues from a scene plan, validate, export SRT / WebVTT.

TIMING IS ESTIMATED. Cues span each scene's planned duration; they are not
aligned to speech. When real TTS/alignment timestamps exist, build cues from
those instead and keep the same export functions.

Stdlib only. Rendering/animation of captions into video lives in assembly.py.
"""
from __future__ import annotations

from dataclasses import dataclass

GAP_SECONDS = 0.1          # silence between consecutive cues
MAX_CHARS_PER_SECOND = 20  # reading-speed warning threshold


@dataclass(frozen=True)
class Cue:
    index: int
    start: float
    end: float
    text: str


def clean_text(text: str) -> str:
    """Single line, collapsed whitespace."""
    return " ".join(str(text).split())


def build_cues(scenes: list[dict], language: str) -> list[Cue]:
    """One cue per scene that has caption text in `language`."""
    cues: list[Cue] = []
    t = 0.0
    for scene in scenes:
        duration = float(scene["estimated_duration_seconds"])
        text = clean_text((scene.get("caption_text") or {}).get(language, ""))
        if text:
            cues.append(Cue(len(cues) + 1, round(t, 3), round(t + max(duration - GAP_SECONDS, 0.1), 3), text))
        t += duration
    return cues


def validate_cues(cues: list[Cue]) -> list[str]:
    """Return a list of problems (empty list = valid)."""
    problems: list[str] = []
    prev_end = 0.0
    for c in cues:
        if not c.text.strip():
            problems.append(f"Cue {c.index} has no text.")
        if c.start < 0 or c.end <= c.start:
            problems.append(f"Cue {c.index} has invalid timing ({c.start}s to {c.end}s).")
        if c.start < prev_end - 1e-6:
            problems.append(f"Cue {c.index} overlaps the previous cue.")
        prev_end = max(prev_end, c.end)
    return problems


def reading_speed_warnings(cues: list[Cue]) -> list[str]:
    out = []
    for c in cues:
        span = c.end - c.start
        if span > 0 and len(c.text) / span > MAX_CHARS_PER_SECOND:
            out.append(f"Cue {c.index} may be too fast to read ({len(c.text)} characters in {span:.1f}s).")
    return out


def _stamp(seconds: float, sep: str) -> str:
    ms_total = int(round(seconds * 1000))
    h, rem = divmod(ms_total, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def to_srt(cues: list[Cue]) -> str:
    blocks = [f"{c.index}\n{_stamp(c.start, ',')} --> {_stamp(c.end, ',')}\n{c.text}\n" for c in cues]
    return "\n".join(blocks)


def _vtt_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def to_vtt(cues: list[Cue]) -> str:
    blocks = [f"{_stamp(c.start, '.')} --> {_stamp(c.end, '.')}\n{_vtt_escape(c.text)}\n" for c in cues]
    return "WEBVTT\n\n" + "\n".join(blocks)
