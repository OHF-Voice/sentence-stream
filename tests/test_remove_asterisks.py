"""Tests for removing asterisks from text (Markdown)."""

import pytest

from sentence_stream import stream_to_sentences
from sentence_stream.util import remove_asterisks


def test_remove_word_asterisks() -> None:
    assert list(
        stream_to_sentences(
            "**Test** sentence with *emphasized* words! Another *** sentence."
        )
    ) == ["Test sentence with emphasized words!", "Another *** sentence."]


def test_remove_line_asterisks() -> None:
    assert (
        remove_asterisks("* Test item 1.\n\n** Test item 2\n * Test item 3.")
        == " Test item 1.\n\n Test item 2\n Test item 3."
    )


@pytest.mark.parametrize(
    "text",
    (
        # Arithmetic, not emphasis: the run starts inside a word.
        "2*3*4 = 24.",
        # Spaced out, so the delimiters can't be markdown emphasis.
        "a * b * c",
        "5 * 5 = 25",
        # Intraword, so not stripped -- and it must not lose only some markers.
        "a**b**c",
        # Not emphasis: nothing but asterisks.
        "Another *** sentence.",
    ),
)
def test_keeps_asterisks_that_are_not_emphasis(text: str) -> None:
    """Text that only looks like markdown must survive unchanged.

    "2*3*4 = 24." used to be rewritten to "234 = 24." -- read aloud, the
    arithmetic simply disappeared.
    """
    assert remove_asterisks(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    (
        ("**Bold** text", "Bold text"),
        ("*emph*", "emph"),
        ("**a** and **b**", "a and b"),
        ("A *word* here.", "A word here."),
        ("(*parenthesized*)", "(parenthesized)"),
    ),
)
def test_removes_emphasis(text: str, expected: str) -> None:
    """Genuine markdown emphasis is still stripped."""
    assert remove_asterisks(text) == expected


def test_line_asterisks_keep_blank_lines() -> None:
    """Stripping a bullet must not swallow the line break before it.

    The leading-whitespace match used to reach across a blank line to the next
    bullet, taking one of the newlines with it -- and a blank line is itself a
    sentence boundary signal.
    """
    assert remove_asterisks("Item one\n\n* Item two") == "Item one\n\n Item two"
