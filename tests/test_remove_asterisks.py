"""Tests for removing asterisks from text (Markdown)."""

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
