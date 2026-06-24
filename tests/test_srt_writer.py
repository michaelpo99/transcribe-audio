from __future__ import annotations

from transcribe_audio.models import SubtitleCue
from transcribe_audio.srt_writer import format_timestamp, write_srt_text


def test_timestamp_and_writer_renumber_cues() -> None:
    cues = [
        SubtitleCue(text="第一行第二行", lines=["第一行", "第二行"], start_ms=1234, end_ms=3500),
        SubtitleCue(text="next", start_ms=3600, end_ms=4000),
    ]

    assert format_timestamp(3_661_007) == "01:01:01,007"
    assert write_srt_text(cues) == (
        "1\n00:00:01,234 --> 00:00:03,500\n第一行\n第二行\n\n"
        "2\n00:00:03,600 --> 00:00:04,000\nnext\n"
    )

