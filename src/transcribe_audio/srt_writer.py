from __future__ import annotations

from pathlib import Path

from .models import SubtitleCue


def format_timestamp(milliseconds: int) -> str:
    if milliseconds < 0:
        raise ValueError("SRT timestamp cannot be negative")
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def write_srt_text(cues: list[SubtitleCue]) -> str:
    blocks: list[str] = []
    for index, cue in enumerate(cues, start=1):
        lines = "\n".join(cue.rendered_lines())
        blocks.append(
            f"{index}\n"
            f"{format_timestamp(cue.start_ms)} --> {format_timestamp(cue.end_ms)}\n"
            f"{lines}"
        )
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def write_srt_file(path: str | Path, cues: list[SubtitleCue]) -> None:
    Path(path).write_text(write_srt_text(cues), encoding="utf-8")

