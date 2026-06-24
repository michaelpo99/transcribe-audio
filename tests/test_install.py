from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_install_deploys_isolated_subtitle_runtime(tmp_path: Path) -> None:
    home = tmp_path / "home"
    bin_dir = home / "bin"
    env = os.environ.copy()
    env["HOME"] = str(home)

    result = subprocess.run(
        ["bash", "install.sh", "--bin-dir", str(bin_dir)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (bin_dir / "transcribe-audio").exists()
    subtitle_bin = bin_dir / "transcribe-audio-subtitle"
    assert subtitle_bin.exists()
    help_result = subprocess.run(
        [str(subtitle_bin), "--help"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert help_result.returncode == 0
    assert "WhisperX word timestamps" in help_result.stdout
