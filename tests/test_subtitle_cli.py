from __future__ import annotations

from pathlib import Path

from transcribe_audio.subtitle_cli import main

FIXTURES = Path(__file__).parent / "fixtures"


def test_cli_writes_expected_srt_atomically(tmp_path: Path) -> None:
    output = tmp_path / "result.srt"
    exit_code = main(
        [
            "--input-json",
            str(FIXTURES / "basic_words.input.json"),
            "--output",
            str(output),
        ]
    )
    assert exit_code == 0
    assert output.read_text(encoding="utf-8") == (
        FIXTURES / "basic_words.expected.srt"
    ).read_text(encoding="utf-8")
    assert list(tmp_path.glob("*.part")) == []


def test_cli_failure_does_not_replace_existing_output(tmp_path: Path) -> None:
    source = tmp_path / "bad.json"
    source.write_text("{}", encoding="utf-8")
    output = tmp_path / "result.srt"
    output.write_text("keep", encoding="utf-8")

    assert main(["--input-json", str(source), "--output", str(output)]) == 2
    assert output.read_text(encoding="utf-8") == "keep"

