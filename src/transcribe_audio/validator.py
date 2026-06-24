from __future__ import annotations

from .models import SubtitleCue


class SubtitleValidationError(ValueError):
    pass


def validate_cues(cues: list[SubtitleCue]) -> None:
    previous_end = 0
    for index, cue in enumerate(cues):
        if not cue.text:
            raise SubtitleValidationError(f"cue {index + 1} has empty text")
        if cue.start_ms < 0 or cue.end_ms <= cue.start_ms:
            raise SubtitleValidationError(f"cue {index + 1} has invalid time range")
        if index and cue.start_ms < previous_end:
            raise SubtitleValidationError(f"cue {index + 1} overlaps the previous cue")
        if len(cue.rendered_lines()) > 2:
            raise SubtitleValidationError(f"cue {index + 1} exceeds two lines")
        previous_end = cue.end_ms


def validate_text_conservation(source_text: str, cues: list[SubtitleCue]) -> None:
    actual = "".join(cue.text for cue in cues)
    if actual != source_text:
        raise SubtitleValidationError("subtitle text was lost, duplicated, or reordered")

