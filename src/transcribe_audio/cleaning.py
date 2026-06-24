from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CleaningResult:
    status: str
    message: str = ""


def resolve_cleaner(explicit: str | None = None) -> str | None:
    override = explicit or os.environ.get("SRT_CLEAN_BIN")
    if override:
        path = Path(override).expanduser()
        return str(path) if path.is_file() and os.access(path, os.X_OK) else None
    discovered = shutil.which("srt-clean")
    if discovered:
        return discovered
    home_candidate = Path.home() / "bin" / "srt-clean"
    if home_candidate.is_file() and os.access(home_candidate, os.X_OK):
        return str(home_candidate)
    return None


def clean_srt(
    input_path: str | Path,
    *,
    profile: str,
    report_output: str | Path,
    cleaner_bin: str | None = None,
) -> CleaningResult:
    source = Path(input_path)
    report = Path(report_output)
    report.unlink(missing_ok=True)
    cleaner = resolve_cleaner(cleaner_bin)
    if cleaner is None:
        return CleaningResult("unavailable", "找不到 srt-clean；保留詞級重切結果")

    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{source.name}.clean.",
        suffix=".srt",
        dir=source.parent,
    )
    os.close(descriptor)
    temp_output = Path(temp_name)
    temp_output.unlink(missing_ok=True)
    command = [
        cleaner,
        "--mode",
        "clean",
        "--profile",
        profile,
        "--level",
        "moderate",
        "--output",
        str(temp_output),
        "--report-output",
        str(report),
        "--force",
        str(source),
    ]
    try:
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        if completed.returncode != 0 or not temp_output.is_file():
            report.unlink(missing_ok=True)
            detail = completed.stderr.strip() or completed.stdout.strip()
            return CleaningResult(
                "failed",
                f"srt-clean 執行失敗；保留詞級重切結果{f': {detail}' if detail else ''}",
            )
        os.replace(temp_output, source)
        return CleaningResult("cleaned")
    except OSError as exc:
        report.unlink(missing_ok=True)
        return CleaningResult("failed", f"srt-clean 無法執行；保留詞級重切結果: {exc}")
    finally:
        temp_output.unlink(missing_ok=True)
