from __future__ import annotations

import stat
from pathlib import Path

from transcribe_audio.cleaning import clean_srt


def _executable(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def test_cleaner_success_replaces_split_srt_and_writes_report(tmp_path: Path) -> None:
    source = tmp_path / "sample.srt"
    source.write_text("before\n", encoding="utf-8")
    report = tmp_path / "sample.clean-report.txt"
    cleaner = _executable(
        tmp_path / "srt-clean",
        """#!/usr/bin/env bash
set -euo pipefail
while (($#)); do
    case "$1" in
        --output) output="$2"; shift 2 ;;
        --report-output) report="$2"; shift 2 ;;
        --profile) profile="$2"; shift 2 ;;
        *) input="$1"; shift ;;
    esac
done
printf 'after:%s\\n' "$profile" > "$output"
printf 'report\\n' > "$report"
""",
    )

    result = clean_srt(
        source,
        profile="jp-adult-soft",
        report_output=report,
        cleaner_bin=str(cleaner),
    )

    assert result.status == "cleaned"
    assert source.read_text(encoding="utf-8") == "after:jp-adult-soft\n"
    assert report.read_text(encoding="utf-8") == "report\n"


def test_missing_or_failed_cleaner_preserves_split_srt(tmp_path: Path) -> None:
    source = tmp_path / "sample.srt"
    source.write_text("split\n", encoding="utf-8")
    report = tmp_path / "report.txt"
    unavailable = clean_srt(
        source,
        profile="jp-adult-soft",
        report_output=report,
        cleaner_bin=str(tmp_path / "missing"),
    )
    assert unavailable.status == "unavailable"
    assert source.read_text(encoding="utf-8") == "split\n"

    cleaner = _executable(tmp_path / "failed-cleaner", "#!/usr/bin/env bash\nexit 4\n")
    failed = clean_srt(
        source,
        profile="jp-adult-soft",
        report_output=report,
        cleaner_bin=str(cleaner),
    )
    assert failed.status == "failed"
    assert source.read_text(encoding="utf-8") == "split\n"
    assert not report.exists()
