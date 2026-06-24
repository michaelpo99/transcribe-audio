from __future__ import annotations

from transcribe_audio.display_width import display_width
from transcribe_audio.models import SourceSegment, WordTiming
from transcribe_audio.segmenter import SegmenterConfig, segment_all, segment_source


def test_word_timestamps_define_split_cue_boundaries() -> None:
    segment = SourceSegment(
        text="こんにちは。今日はいい天気です。",
        start_ms=0,
        end_ms=4000,
        words=[
            WordTiming("こんにちは。", 100, 1200),
            WordTiming("今日は", 1500, 2200),
            WordTiming("いい天気です。", 2300, 3900),
        ],
    )
    cues = segment_source(
        segment,
        SegmenterConfig(natural_boundary_min_columns=4),
    )
    assert [cue.text for cue in cues] == ["こんにちは。", "今日はいい天気です。"]
    assert [(cue.start_ms, cue.end_ms) for cue in cues] == [(100, 1200), (1500, 3900)]
    assert all(cue.timing_source == "word" for cue in cues)


def test_long_unspaced_japanese_is_split_to_two_line_capacity() -> None:
    text = "日" * 100
    cues = segment_source(
        SourceSegment(text=text, start_ms=0, end_ms=10_000, words=[WordTiming(text)]),
    )
    assert "".join(cue.text for cue in cues) == text
    assert len(cues) >= 3
    assert all(len(cue.lines) <= 2 for cue in cues)
    assert all(display_width(line) <= 42 for cue in cues for line in cue.lines)
    assert all(cue.end_ms - cue.start_ms <= 7000 for cue in cues)


def test_short_punctuation_group_merges_when_safe() -> None:
    segment = SourceSegment(
        text="はい。続きます。",
        start_ms=0,
        end_ms=2000,
        words=[
            WordTiming("はい。", 0, 400),
            WordTiming("続きます。", 450, 1800),
        ],
    )
    cues = segment_source(segment)
    assert [cue.text for cue in cues] == ["はい。続きます。"]


def test_cross_segment_overlap_is_clamped() -> None:
    cues = segment_all(
        [
            SourceSegment("a", 0, 1000, [WordTiming("a", 0, 1000)]),
            SourceSegment("b", 900, 2000, [WordTiming("b", 900, 2000)]),
        ]
    )
    assert cues[0].end_ms == 950
    assert cues[1].start_ms == 950


def test_single_long_word_is_split_by_duration() -> None:
    cues = segment_source(
        SourceSegment("abcdefghij", 0, 10_000, [WordTiming("abcdefghij", 0, 10_000)])
    )
    assert "".join(cue.text for cue in cues) == "abcdefghij"
    assert len(cues) == 2
    assert all(cue.end_ms - cue.start_ms <= 7000 for cue in cues)


def test_sparse_fallback_text_is_capped_instead_of_staying_on_screen() -> None:
    cues = segment_source(SourceSegment("あ", 0, 20_000))
    assert [(cue.text, cue.start_ms, cue.end_ms) for cue in cues] == [("あ", 0, 7000)]
    assert cues[0].timing_source == "proportional"


def test_english_word_spacing_is_reconciled_without_losing_word_timing() -> None:
    segment = SourceSegment(
        text=" Hello world. Next line.",
        start_ms=0,
        end_ms=3000,
        words=[
            WordTiming("Hello", 100, 700),
            WordTiming("world.", 800, 1400),
            WordTiming("Next", 1600, 2100),
            WordTiming("line.", 2200, 2900),
        ],
    )
    cues = segment_source(segment, SegmenterConfig(natural_boundary_min_columns=4))
    assert "".join(cue.text for cue in cues) == segment.text
    assert [(cue.start_ms, cue.end_ms) for cue in cues] == [(100, 1400), (1600, 2900)]
    assert all(cue.timing_source == "word" for cue in cues)
