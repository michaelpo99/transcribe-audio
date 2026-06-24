from __future__ import annotations

import math
from dataclasses import dataclass

from .display_width import display_width, split_text_to_width, wrap_tokens
from .models import SourceSegment, SubtitleCue, WordTiming
from .timing import fill_word_timings
from .validator import validate_cues, validate_text_conservation

STRONG_PUNCTUATION = frozenset("。！？.!?")
WEAK_PUNCTUATION = frozenset("、，,;；:：")


@dataclass(frozen=True, slots=True)
class SegmenterConfig:
    max_line_columns: int = 42
    max_lines: int = 2
    min_duration_ms: int = 800
    max_duration_ms: int = 7000
    pause_boundary_ms: int = 650
    natural_boundary_min_columns: int = 16

    @property
    def max_cue_columns(self) -> int:
        return self.max_line_columns * self.max_lines


def _reconcile_words_with_text(segment: SourceSegment) -> list[WordTiming] | None:
    if not segment.words:
        return []
    reconciled: list[WordTiming] = []
    cursor = 0
    for word in segment.words:
        position = segment.text.find(word.text, cursor)
        if position < 0:
            return None
        gap = segment.text[cursor:position]
        if reconciled:
            reconciled[-1].text += gap
            reconciled.append(WordTiming(word.text, word.start_ms, word.end_ms))
        else:
            reconciled.append(WordTiming(gap + word.text, word.start_ms, word.end_ms))
        cursor = position + len(word.text)
    reconciled[-1].text += segment.text[cursor:]
    return reconciled


def _explode_oversized_words(
    words: list[WordTiming],
    config: SegmenterConfig,
) -> list[WordTiming]:
    exploded: list[WordTiming] = []
    for word in words:
        word_width = display_width(word.text)
        duration = (
            word.end_ms - word.start_ms
            if word.start_ms is not None and word.end_ms is not None
            else 0
        )
        piece_count = max(
            1,
            math.ceil(word_width / config.max_cue_columns),
            math.ceil(duration / config.max_duration_ms),
        )
        if piece_count == 1:
            exploded.append(word)
            continue
        target_columns = max(1, math.ceil(word_width / piece_count))
        pieces = split_text_to_width(word.text, target_columns)
        if word.start_ms is None or word.end_ms is None:
            exploded.extend(WordTiming(piece) for piece in pieces)
            continue
        weights = [max(1, display_width(piece)) for piece in pieces]
        total = sum(weights)
        elapsed = 0
        for index, (piece, weight) in enumerate(zip(pieces, weights)):
            start_ms = word.start_ms + round(duration * elapsed / total)
            elapsed += weight
            end_ms = word.start_ms + round(duration * elapsed / total)
            if index == len(pieces) - 1:
                end_ms = word.end_ms
            exploded.append(WordTiming(piece, start_ms, max(start_ms + 1, end_ms)))
    return exploded


def _is_strong_boundary(word: WordTiming) -> bool:
    return bool(word.text.rstrip()) and word.text.rstrip()[-1] in STRONG_PUNCTUATION


def _is_weak_boundary(word: WordTiming) -> bool:
    return bool(word.text.rstrip()) and word.text.rstrip()[-1] in WEAK_PUNCTUATION


def _pause_after(words: list[WordTiming], index: int) -> int:
    if index + 1 >= len(words):
        return 0
    end_ms = words[index].end_ms
    next_start = words[index + 1].start_ms
    if end_ms is None or next_start is None:
        return 0
    return max(0, next_start - end_ms)


def _group_words(words: list[WordTiming], config: SegmenterConfig) -> list[list[WordTiming]]:
    groups: list[list[WordTiming]] = []
    current: list[WordTiming] = []

    for index, word in enumerate(words):
        if current:
            candidate = current + [word]
            candidate_width = display_width("".join(item.text for item in candidate))
            candidate_duration = int(candidate[-1].end_ms or 0) - int(candidate[0].start_ms or 0)
            if (
                candidate_width > config.max_cue_columns
                or candidate_duration > config.max_duration_ms
            ):
                groups.append(current)
                current = []

        current.append(word)
        current_width = display_width("".join(item.text for item in current))
        current_duration = int(current[-1].end_ms or 0) - int(current[0].start_ms or 0)
        strong = _is_strong_boundary(word)
        pause = _pause_after(words, index) >= config.pause_boundary_ms
        weak = _is_weak_boundary(word)
        natural_size = current_width >= config.natural_boundary_min_columns
        if current_duration >= config.min_duration_ms and (
            strong or pause or (weak and natural_size)
        ):
            groups.append(current)
            current = []

    if current:
        groups.append(current)
    return groups


def _merge_short_groups(
    groups: list[list[WordTiming]],
    config: SegmenterConfig,
) -> list[list[WordTiming]]:
    merged: list[list[WordTiming]] = []
    index = 0
    while index < len(groups):
        current = groups[index]
        duration = int(current[-1].end_ms or 0) - int(current[0].start_ms or 0)
        if duration >= config.min_duration_ms:
            merged.append(current)
            index += 1
            continue

        if index + 1 < len(groups):
            candidate = current + groups[index + 1]
            width = display_width("".join(word.text for word in candidate))
            candidate_duration = int(candidate[-1].end_ms or 0) - int(
                candidate[0].start_ms or 0
            )
            if (
                width <= config.max_cue_columns
                and candidate_duration <= config.max_duration_ms
            ):
                merged.append(candidate)
                index += 2
                continue

        if merged:
            candidate = merged[-1] + current
            width = display_width("".join(word.text for word in candidate))
            candidate_duration = int(candidate[-1].end_ms or 0) - int(
                candidate[0].start_ms or 0
            )
            if (
                width <= config.max_cue_columns
                and candidate_duration <= config.max_duration_ms
            ):
                merged[-1] = candidate
                index += 1
                continue

        merged.append(current)
        index += 1
    return merged


def segment_source(
    segment: SourceSegment,
    config: SegmenterConfig | None = None,
) -> list[SubtitleCue]:
    config = config or SegmenterConfig()
    reconciled_words = _reconcile_words_with_text(segment)
    timing_segment = (
        SourceSegment(
            text=segment.text,
            start_ms=segment.start_ms,
            end_ms=segment.end_ms,
            words=reconciled_words,
            index=segment.index,
        )
        if reconciled_words is not None
        else SourceSegment(
            text=segment.text,
            start_ms=segment.start_ms,
            end_ms=segment.end_ms,
            words=[WordTiming(segment.text)],
            index=segment.index,
        )
    )
    words, timing_source = fill_word_timings(timing_segment)
    if reconciled_words is None:
        timing_source = "proportional"
    words = _explode_oversized_words(words, config)

    word_text = "".join(word.text for word in words)
    if word_text != segment.text:
        words, timing_source = fill_word_timings(
            SourceSegment(
                text=segment.text,
                start_ms=segment.start_ms,
                end_ms=segment.end_ms,
                words=[WordTiming(segment.text)],
                index=segment.index,
            )
        )
        words = _explode_oversized_words(words, config)
        timing_source = "proportional"

    groups = _merge_short_groups(_group_words(words, config), config)
    cues: list[SubtitleCue] = []
    for group in groups:
        text = "".join(word.text for word in group)
        lines = wrap_tokens([word.text for word in group], config.max_line_columns, config.max_lines)
        start_ms = max(segment.start_ms, int(group[0].start_ms or segment.start_ms))
        end_ms = min(segment.end_ms, int(group[-1].end_ms or segment.end_ms))
        if timing_source != "word" and end_ms - start_ms > config.max_duration_ms:
            end_ms = start_ms + config.max_duration_ms
        cues.append(
            SubtitleCue(
                text=text,
                lines=lines,
                start_ms=start_ms,
                end_ms=end_ms,
                source_segment_index=segment.index,
                timing_source=timing_source,
            )
        )
    validate_cues(cues)
    validate_text_conservation(segment.text, cues)
    return cues


def segment_all(
    segments: list[SourceSegment],
    config: SegmenterConfig | None = None,
) -> list[SubtitleCue]:
    cues: list[SubtitleCue] = []
    previous_end = 0
    for segment in segments:
        segment_cues = segment_source(segment, config)
        for cue in segment_cues:
            if cue.start_ms < previous_end:
                previous = cues[-1]
                boundary = round((previous.end_ms + cue.start_ms) / 2)
                boundary = max(previous.start_ms + 1, boundary)
                boundary = min(cue.end_ms - 1, boundary)
                previous.end_ms = boundary
                cue.start_ms = boundary
            if cue.end_ms <= cue.start_ms:
                raise ValueError("overlapping source segments cannot form valid subtitle cues")
            previous_end = cue.end_ms
            cues.append(cue)
    validate_cues(cues)
    return cues
