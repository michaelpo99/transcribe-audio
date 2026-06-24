from __future__ import annotations

from dataclasses import replace

from .display_width import display_width
from .models import SourceSegment, WordTiming


def _weights(words: list[WordTiming]) -> list[int]:
    return [max(1, display_width(word.text)) for word in words]


def _distribute(
    words: list[WordTiming],
    start_ms: int,
    end_ms: int,
) -> list[WordTiming]:
    weights = _weights(words)
    total_weight = sum(weights)
    duration = max(len(words), end_ms - start_ms)
    result: list[WordTiming] = []
    elapsed_weight = 0
    for index, (word, weight) in enumerate(zip(words, weights)):
        word_start = start_ms + round(duration * elapsed_weight / total_weight)
        elapsed_weight += weight
        word_end = start_ms + round(duration * elapsed_weight / total_weight)
        if index == len(words) - 1:
            word_end = end_ms
        if word_end <= word_start:
            word_end = word_start + 1
        result.append(replace(word, start_ms=word_start, end_ms=word_end))
    return result


def fill_word_timings(segment: SourceSegment) -> tuple[list[WordTiming], str]:
    if not segment.words:
        return (
            _distribute([WordTiming(segment.text)], segment.start_ms, segment.end_ms),
            "proportional",
        )

    complete = [
        word.start_ms is not None
        and word.end_ms is not None
        and word.end_ms > word.start_ms
        for word in segment.words
    ]
    if not any(complete):
        return _distribute(segment.words, segment.start_ms, segment.end_ms), "proportional"
    if all(complete):
        return [replace(word) for word in segment.words], "word"

    result = [replace(word) for word in segment.words]
    index = 0
    while index < len(result):
        if complete[index]:
            index += 1
            continue
        run_start = index
        while index < len(result) and not complete[index]:
            index += 1
        run_end = index
        left_ms = (
            result[run_start - 1].end_ms
            if run_start > 0 and result[run_start - 1].end_ms is not None
            else segment.start_ms
        )
        right_ms = (
            result[run_end].start_ms
            if run_end < len(result) and result[run_end].start_ms is not None
            else segment.end_ms
        )
        left_ms = max(segment.start_ms, int(left_ms))
        right_ms = min(segment.end_ms, int(right_ms))
        if right_ms - left_ms < run_end - run_start:
            right_ms = min(segment.end_ms, left_ms + (run_end - run_start))
        distributed = _distribute(result[run_start:run_end], left_ms, right_ms)
        result[run_start:run_end] = distributed

    previous_end = segment.start_ms
    for word in result:
        word.start_ms = max(previous_end, segment.start_ms, int(word.start_ms or previous_end))
        word.end_ms = min(segment.end_ms, int(word.end_ms or word.start_ms + 1))
        if word.end_ms <= word.start_ms:
            word.end_ms = min(segment.end_ms, word.start_ms + 1)
        previous_end = word.end_ms
    return result, "interpolated"

