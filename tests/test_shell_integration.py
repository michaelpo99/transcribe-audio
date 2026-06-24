from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_executable(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def test_repo_subtitle_wrapper_is_directly_runnable() -> None:
    result = subprocess.run(
        [str(REPO_ROOT / "bin" / "transcribe-audio-subtitle"), "--help"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert "WhisperX word timestamps" in result.stdout


def _fake_environment(tmp_path: Path) -> dict[str, str]:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    _write_executable(
        fake_bin / "python",
        """#!/usr/bin/env bash
cat <<'EOF'
python_version=3.12.0
whisperx_version=test
torch_version=test
cuda_available=False
cuda_runtime=
gpu_name=
vram_mb=0
import_error=
EOF
""",
    )
    _write_executable(
        fake_bin / "whisperx",
        """#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "--help" ]]; then
    exit 0
fi
input="$1"
shift
output_dir=""
output_format=""
while (($#)); do
    case "$1" in
        --output_dir) output_dir="$2"; shift 2 ;;
        --output_format) output_format="$2"; shift 2 ;;
        *) shift ;;
    esac
done
stem="$(basename "${input%.*}")"
mkdir -p "$output_dir"
cat > "$output_dir/$stem.srt" <<'EOF'
1
00:00:00,000 --> 00:00:04,000
こんにちは。今日はいい天気です。
EOF
if [[ "$output_format" == "all" ]]; then
    cat > "$output_dir/$stem.json" <<'EOF'
{"segments":[{"start":0.0,"end":4.0,"text":"こんにちは。今日はいい天気です。","words":[{"word":"こんにちは。","start":0.1,"end":1.2},{"word":"今日は","start":1.5,"end":2.2},{"word":"いい天気です。","start":2.3,"end":3.9}]}]}
EOF
    printf 'こんにちは。今日はいい天気です。\\n' > "$output_dir/$stem.txt"
fi
""",
    )
    subtitle_bin = tmp_path / "transcribe-audio-subtitle"
    _write_executable(
        subtitle_bin,
        f"""#!/usr/bin/env bash
PYTHONPATH={REPO_ROOT / "src"} exec {sys.executable} -m transcribe_audio.subtitle_cli "$@"
""",
    )
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["TRANSCRIBE_AUDIO_SUBTITLE_BIN"] = str(subtitle_bin)
    return env


def _run_transcribe(target: Path, env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            str(REPO_ROOT / "bin" / "transcribe-audio"),
            "--file",
            str(target / "sample.wav"),
            "--device",
            "cpu",
            "--model",
            "tiny",
            "--batch-size",
            "1",
            "--compute-type",
            "int8",
            *args,
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_split_mode_keeps_raw_and_hides_internal_json(tmp_path: Path) -> None:
    target = tmp_path / "media"
    target.mkdir()
    (target / "sample.wav").write_bytes(b"fake")

    result = _run_transcribe(
        target,
        _fake_environment(tmp_path),
        "--output-format",
        "srt",
        "--subtitle-postprocess",
        "split",
    )

    assert result.returncode == 0, result.stderr
    transcript = target / "transcript"
    assert (transcript / "sample.whisperx.raw.srt").exists()
    assert (transcript / "sample.srt").read_text(encoding="utf-8").count("-->") == 2
    assert not (transcript / "sample.json").exists()


def test_off_mode_preserves_original_srt_behavior(tmp_path: Path) -> None:
    target = tmp_path / "media"
    target.mkdir()
    (target / "sample.wav").write_bytes(b"fake")
    env = _fake_environment(tmp_path)
    env.pop("TRANSCRIBE_AUDIO_SUBTITLE_BIN")

    result = _run_transcribe(
        target,
        env,
        "--output-format",
        "srt",
        "--subtitle-postprocess",
        "off",
    )

    assert result.returncode == 0, result.stderr
    transcript = target / "transcript"
    assert (transcript / "sample.srt").read_text(encoding="utf-8").count("-->") == 1
    assert not (transcript / "sample.whisperx.raw.srt").exists()


def test_postprocess_failure_keeps_raw_without_partial_main_srt(tmp_path: Path) -> None:
    target = tmp_path / "media"
    target.mkdir()
    (target / "sample.wav").write_bytes(b"fake")
    env = _fake_environment(tmp_path)
    failing_subtitle = tmp_path / "failing-subtitle"
    _write_executable(failing_subtitle, "#!/usr/bin/env bash\nexit 9\n")
    env["TRANSCRIBE_AUDIO_SUBTITLE_BIN"] = str(failing_subtitle)

    result = _run_transcribe(
        target,
        env,
        "--output-format",
        "srt",
        "--subtitle-postprocess",
        "split",
    )

    assert result.returncode == 3
    transcript = target / "transcript"
    assert (transcript / "sample.whisperx.raw.srt").exists()
    assert not (transcript / "sample.srt").exists()
    assert "subtitle_postprocess_failed" in (
        transcript / "_failed-files.txt"
    ).read_text(encoding="utf-8")


def test_clean_mode_maps_japanese_profile_and_keeps_report(tmp_path: Path) -> None:
    target = tmp_path / "media"
    target.mkdir()
    (target / "sample.wav").write_bytes(b"fake")
    env = _fake_environment(tmp_path)
    cleaner_log = tmp_path / "cleaner-profile.txt"
    cleaner = tmp_path / "srt-clean"
    _write_executable(
        cleaner,
        f"""#!/usr/bin/env bash
set -euo pipefail
while (($#)); do
    case "$1" in
        --output) output="$2"; shift 2 ;;
        --report-output) report="$2"; shift 2 ;;
        --profile) profile="$2"; shift 2 ;;
        --mode|--level) shift 2 ;;
        --force) shift ;;
        *) input="$1"; shift ;;
    esac
done
cp "$input" "$output"
printf '%s\\n' "$profile" > {cleaner_log}
printf 'cleaned\\n' > "$report"
""",
    )
    env["SRT_CLEAN_BIN"] = str(cleaner)

    result = _run_transcribe(
        target,
        env,
        "--language",
        "ja",
        "--output-format",
        "srt",
        "--subtitle-postprocess",
        "clean",
    )

    assert result.returncode == 0, result.stderr
    assert cleaner_log.read_text(encoding="utf-8") == "jp-adult-soft\n"
    assert (target / "transcript" / "sample.clean-report.txt").exists()


def test_clean_mode_without_cleaner_warns_and_keeps_split_result(tmp_path: Path) -> None:
    target = tmp_path / "media"
    target.mkdir()
    (target / "sample.wav").write_bytes(b"fake")
    env = _fake_environment(tmp_path)
    env["SRT_CLEAN_BIN"] = str(tmp_path / "missing-cleaner")

    result = _run_transcribe(
        target,
        env,
        "--language",
        "ja",
        "--output-format",
        "srt",
        "--subtitle-postprocess",
        "clean",
    )

    assert result.returncode == 0
    assert result.stderr.count("找不到 srt-clean") == 1
    assert (target / "transcript" / "sample.srt").read_text(
        encoding="utf-8"
    ).count("-->") == 2


def test_all_mode_preserves_public_outputs_and_replaces_only_srt(tmp_path: Path) -> None:
    target = tmp_path / "media"
    target.mkdir()
    (target / "sample.wav").write_bytes(b"fake")

    result = _run_transcribe(
        target,
        _fake_environment(tmp_path),
        "--output-format",
        "all",
        "--subtitle-postprocess",
        "split",
    )

    assert result.returncode == 0, result.stderr
    transcript = target / "transcript"
    assert (transcript / "sample.txt").exists()
    assert (transcript / "sample.json").exists()
    assert (transcript / "sample.whisperx.raw.srt").exists()
    assert (transcript / "sample.srt").read_text(encoding="utf-8").count("-->") == 2
