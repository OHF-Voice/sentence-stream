"""Utility methods."""

import regex as re

WORD_ASTERISKS = re.compile(r"\*+([^\*]+)\*+")
LINE_ASTERICKS = re.compile(r"(?<=^|\n)\s*\*+")


def remove_asterisks(text: str) -> str:
    """Remove *asterisks* surrounding **words**"""
    text = WORD_ASTERISKS.sub(r"\1", text)
    text = LINE_ASTERICKS.sub("", text)
    return text
