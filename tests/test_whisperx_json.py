from __future__ import annotations

import pytest

from transcribe_audio.whisperx_json import WhisperXJSONError, parse_whisperx_data


def test_parse_segments_and_optional_word_timestamps() -> None:
    segments = parse_whisperx_data(
        {
            "segments": [
                {
                    "start": 1.2344,
                    "end": 3.5,
                    "text": "こんにちは。",
                    "words": [
                        {"word": "こんにちは", "start": 1.2344, "end": 2.8},
                        {"word": "。"},
                    ],
                }
            ]
        }
    )

    assert segments[0].start_ms == 1234
    assert segments[0].end_ms == 3500
    assert segments[0].words[0].start_ms == 1234
    assert segments[0].words[1].start_ms is None


@pytest.mark.parametrize(
    "data, message",
    [
        ({}, "segments must be a list"),
        ({"segments": [{"start": 1, "end": 1, "text": "x"}]}, "greater than start"),
        ({"segments": [{"start": 1, "end": 2, "text": 3}]}, "text must be a string"),
    ],
)
def test_invalid_whisperx_data_fails(data: object, message: str) -> None:
    with pytest.raises(WhisperXJSONError, match=message):
        parse_whisperx_data(data)

