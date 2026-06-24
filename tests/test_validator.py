from __future__ import annotations

import pytest

from transcribe_audio.models import SubtitleCue
from transcribe_audio.validator import (
    SubtitleValidationError,
    validate_cues,
    validate_text_conservation,
)


def test_validate_valid_cues_and_text_conservation() -> None:
    cues = [
        SubtitleCue(text="abc", start_ms=0, end_ms=1000),
        SubtitleCue(text="def", start_ms=1000, end_ms=2000),
    ]
    validate_cues(cues)
    validate_text_conservation("abcdef", cues)


def test_validate_rejects_overlap() -> None:
    cues = [
        SubtitleCue(text="a", start_ms=0, end_ms=1000),
        SubtitleCue(text="b", start_ms=999, end_ms=2000),
    ]
    with pytest.raises(SubtitleValidationError, match="overlaps"):
        validate_cues(cues)


def test_validate_detects_text_loss() -> None:
    with pytest.raises(SubtitleValidationError, match="lost"):
        validate_text_conservation(
            "abcdef",
            [SubtitleCue(text="abc", start_ms=0, end_ms=1000)],
        )
