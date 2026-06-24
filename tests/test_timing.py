from __future__ import annotations

from transcribe_audio.models import SourceSegment, WordTiming
from transcribe_audio.timing import fill_word_timings


def test_complete_word_timing_is_preserved() -> None:
    words, source = fill_word_timings(
        SourceSegment(
            text="ab",
            start_ms=0,
            end_ms=1000,
            words=[WordTiming("a", 10, 400), WordTiming("b", 500, 900)],
        )
    )
    assert source == "word"
    assert [(word.start_ms, word.end_ms) for word in words] == [(10, 400), (500, 900)]


def test_missing_run_is_interpolated_between_anchors() -> None:
    words, source = fill_word_timings(
        SourceSegment(
            text="abc",
            start_ms=0,
            end_ms=1000,
            words=[
                WordTiming("a", 0, 200),
                WordTiming("b"),
                WordTiming("c", 800, 1000),
            ],
        )
    )
    assert source == "interpolated"
    assert (words[1].start_ms, words[1].end_ms) == (200, 800)


def test_no_word_timing_uses_proportional_width() -> None:
    words, source = fill_word_timings(
        SourceSegment(
            text="日a",
            start_ms=0,
            end_ms=3000,
            words=[WordTiming("日"), WordTiming("a")],
        )
    )
    assert source == "proportional"
    assert words[0].end_ms == 2000
    assert words[1].start_ms == 2000

