from __future__ import annotations

from transcribe_audio.display_width import display_width, split_text_to_width, wrap_tokens


def test_cjk_and_combining_display_width() -> None:
    assert display_width("abc") == 3
    assert display_width("日本") == 4
    assert display_width("e\u0301") == 1


def test_split_and_wrap_preserve_text() -> None:
    text = "日本語abcdef"
    parts = split_text_to_width(text, 6)
    assert "".join(parts) == text
    lines = wrap_tokens(parts, 6, 2)
    assert "".join(lines) == text
    assert all(display_width(line) <= 6 for line in lines)

