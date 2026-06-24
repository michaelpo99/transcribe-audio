from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .models import SourceSegment, WordTiming


class WhisperXJSONError(ValueError):
    pass


def seconds_to_ms(value: Any, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WhisperXJSONError(f"{label} must be a number")
    if not math.isfinite(float(value)) or value < 0:
        raise WhisperXJSONError(f"{label} must be a finite non-negative number")
    return round(float(value) * 1000)


def _optional_ms(value: Any, *, label: str) -> int | None:
    if value is None:
        return None
    return seconds_to_ms(value, label=label)


def parse_whisperx_data(data: Any) -> list[SourceSegment]:
    if not isinstance(data, dict):
        raise WhisperXJSONError("WhisperX JSON root must be an object")
    raw_segments = data.get("segments")
    if not isinstance(raw_segments, list):
        raise WhisperXJSONError("WhisperX JSON segments must be a list")

    segments: list[SourceSegment] = []
    for index, raw_segment in enumerate(raw_segments):
        label = f"segments[{index}]"
        if not isinstance(raw_segment, dict):
            raise WhisperXJSONError(f"{label} must be an object")
        text = raw_segment.get("text", "")
        if not isinstance(text, str):
            raise WhisperXJSONError(f"{label}.text must be a string")
        start_ms = seconds_to_ms(raw_segment.get("start"), label=f"{label}.start")
        end_ms = seconds_to_ms(raw_segment.get("end"), label=f"{label}.end")
        if end_ms <= start_ms:
            raise WhisperXJSONError(f"{label}.end must be greater than start")

        raw_words = raw_segment.get("words", [])
        if raw_words is None:
            raw_words = []
        if not isinstance(raw_words, list):
            raise WhisperXJSONError(f"{label}.words must be a list")

        words: list[WordTiming] = []
        for word_index, raw_word in enumerate(raw_words):
            word_label = f"{label}.words[{word_index}]"
            if not isinstance(raw_word, dict):
                raise WhisperXJSONError(f"{word_label} must be an object")
            word_text = raw_word.get("word", "")
            if not isinstance(word_text, str):
                raise WhisperXJSONError(f"{word_label}.word must be a string")
            if not word_text:
                continue
            word_start = _optional_ms(raw_word.get("start"), label=f"{word_label}.start")
            word_end = _optional_ms(raw_word.get("end"), label=f"{word_label}.end")
            if word_start is not None and word_end is not None and word_end <= word_start:
                raise WhisperXJSONError(f"{word_label}.end must be greater than start")
            words.append(WordTiming(text=word_text, start_ms=word_start, end_ms=word_end))

        segments.append(
            SourceSegment(
                text=text,
                start_ms=start_ms,
                end_ms=end_ms,
                words=words,
                index=index,
            )
        )
    return segments


def load_whisperx_json(path: str | Path) -> list[SourceSegment]:
    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8-sig"))
    except OSError as exc:
        raise WhisperXJSONError(f"cannot read WhisperX JSON: {source}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise WhisperXJSONError(f"invalid WhisperX JSON: {source}: {exc}") from exc
    return parse_whisperx_data(data)

