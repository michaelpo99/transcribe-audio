from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

from .cleaning import clean_srt
from .segmenter import SegmenterConfig, segment_all
from .srt_writer import write_srt_file
from .validator import SubtitleValidationError
from .whisperx_json import WhisperXJSONError, load_whisperx_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="transcribe-audio-subtitle",
        description="Build readable SRT subtitles from WhisperX word timestamps.",
    )
    parser.add_argument("--input-json", required=True, help="WhisperX alignment JSON")
    parser.add_argument("--output", required=True, help="Final SRT output path")
    parser.add_argument("--max-line-columns", type=int, default=42)
    parser.add_argument("--max-lines", type=int, default=2)
    parser.add_argument("--min-duration-ms", type=int, default=800)
    parser.add_argument("--max-duration-ms", type=int, default=7000)
    parser.add_argument("--pause-boundary-ms", type=int, default=650)
    parser.add_argument("--clean-profile", help="Run srt-clean with this profile")
    parser.add_argument("--clean-report", help="srt-clean report output path")
    parser.add_argument("--cleaner-bin", help="Explicit srt-clean executable")
    return parser


def _positive(value: int, *, label: str) -> int:
    if value <= 0:
        raise ValueError(f"{label} must be positive")
    return value


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = SegmenterConfig(
        max_line_columns=_positive(args.max_line_columns, label="--max-line-columns"),
        max_lines=_positive(args.max_lines, label="--max-lines"),
        min_duration_ms=_positive(args.min_duration_ms, label="--min-duration-ms"),
        max_duration_ms=_positive(args.max_duration_ms, label="--max-duration-ms"),
        pause_boundary_ms=_positive(args.pause_boundary_ms, label="--pause-boundary-ms"),
    )
    if config.min_duration_ms > config.max_duration_ms:
        raise ValueError("--min-duration-ms cannot exceed --max-duration-ms")

    segments = load_whisperx_json(args.input_json)
    cues = segment_all(segments, config)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{output.name}.",
        suffix=".part",
        dir=output.parent,
    )
    os.close(descriptor)
    temp_path = Path(temp_name)
    try:
        write_srt_file(temp_path, cues)
        os.replace(temp_path, output)
    finally:
        temp_path.unlink(missing_ok=True)
    if args.clean_profile:
        report_output = (
            Path(args.clean_report)
            if args.clean_report
            else output.with_name(f"{output.stem}.clean-report.txt")
        )
        cleaning_result = clean_srt(
            output,
            profile=args.clean_profile,
            report_output=report_output,
            cleaner_bin=args.cleaner_bin,
        )
        if cleaning_result.status != "cleaned":
            print(f"warning: {cleaning_result.message}", file=sys.stderr)
        else:
            print(f"cleaned subtitle: {output} (profile={args.clean_profile})")
    print(f"wrote subtitle: {output} ({len(cues)} split cues)")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return run(argv)
    except (OSError, ValueError, WhisperXJSONError, SubtitleValidationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
