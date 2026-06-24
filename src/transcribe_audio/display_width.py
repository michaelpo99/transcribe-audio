from __future__ import annotations

import unicodedata


def char_width(character: str) -> int:
    if character in {"\n", "\r"}:
        return 0
    if unicodedata.combining(character):
        return 0
    return 2 if unicodedata.east_asian_width(character) in {"W", "F"} else 1


def display_width(text: str) -> int:
    return sum(char_width(character) for character in text)


def split_text_to_width(text: str, max_columns: int) -> list[str]:
    if max_columns <= 0:
        raise ValueError("max_columns must be positive")
    parts: list[str] = []
    current: list[str] = []
    current_width = 0
    for character in text:
        width = char_width(character)
        if current and current_width + width > max_columns:
            parts.append("".join(current))
            current = []
            current_width = 0
        current.append(character)
        current_width += width
    if current:
        parts.append("".join(current))
    return parts


def wrap_tokens(tokens: list[str], max_columns: int, max_lines: int = 2) -> list[str]:
    if not tokens:
        return []
    lines: list[str] = []
    current = ""
    for token in tokens:
        pieces = split_text_to_width(token, max_columns)
        for piece in pieces:
            if current and display_width(current + piece) > max_columns:
                lines.append(current)
                current = piece
            else:
                current += piece
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        raise ValueError("text exceeds configured line capacity")
    return lines

