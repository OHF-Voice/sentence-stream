"""Utility methods."""

import regex as re

# Markdown emphasis around a word. Two guards keep it from eating text that only
# looks like markup:
#
#   * the run may not start inside a word, so "2*3*4" keeps its arithmetic
#   * the emphasized text may not begin or end with a space, so the spaced-out
#     multiplication in "a * b * c" is left alone
#
# Both cases used to be rewritten -- "2*3*4 = 24." was read aloud as "234 = 24."
# The lookbehind excludes ``*`` as well as letters and digits, or the match could
# start midway through a run and leave a stray marker behind ("a**b**c" -> "a*bc").
WORD_ASTERISKS = re.compile(r"(?<![\p{L}\p{N}*])\*+([^\s*](?:[^*]*[^\s*])?)\*+")
# A markdown bullet's asterisks, plus any indent before them. The leading
# whitespace deliberately excludes newlines: \s* here would reach across a blank
# line to the next bullet and swallow the line break with it.
LINE_ASTERISKS = re.compile(r"(?<=^|\n)[^\S\n]*\*+")


def remove_asterisks(text: str) -> str:
    """Remove *asterisks* surrounding **words**"""
    text = WORD_ASTERISKS.sub(r"\1", text)
    text = LINE_ASTERISKS.sub("", text)
    return text
