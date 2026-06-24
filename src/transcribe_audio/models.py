from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

TimingSource = Literal["word", "interpolated", "proportional"]


@dataclass(slots=True)
class WordTiming:
    text: str
    start_ms: int | None = None
    end_ms: int | None = None


@dataclass(slots=True)
class SourceSegment:
    text: str
    start_ms: int
    end_ms: int
    words: list[WordTiming] = field(default_factory=list)
    index: int = 0


@dataclass(slots=True)
class SubtitleCue:
    text: str
    start_ms: int
    end_ms: int
    lines: list[str] = field(default_factory=list)
    source_segment_index: int = 0
    timing_source: TimingSource = "word"

    def rendered_lines(self) -> list[str]:
        return self.lines or [self.text]

