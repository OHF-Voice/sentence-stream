"""Tests for sentence boundary detection."""

from typing import List

import pytest

from sentence_stream import async_stream_to_sentences, stream_to_sentences

from .english_golden_rules import GOLDEN_EN_RULES


@pytest.mark.asyncio
async def test_one_chunk() -> None:
    """Test that a single text chunk produces a single sentence."""
    text = "Test chunk"
    assert list(stream_to_sentences([text])) == [text]

    async def text_gen():
        yield text

    assert [sent async for sent in async_stream_to_sentences(text_gen())] == [text]


@pytest.mark.parametrize("punctuation", (".", "?", "!", "!?"))
@pytest.mark.asyncio
async def test_one_chunk_with_punctuation(punctuation: str) -> None:
    """Test that punctuation splits sentences in a single chunk."""
    text_1 = f"Test chunk 1{punctuation}"
    text_2 = "Test chunk 2"
    text = f"{text_1} {text_2}"

    assert list(stream_to_sentences([text])) == [text_1, text_2]

    async def text_gen():
        yield text

    assert [sent async for sent in async_stream_to_sentences(text_gen())] == [
        text_1,
        text_2,
    ]


@pytest.mark.asyncio
async def test_multiple_chunks() -> None:
    """Test sentence splitting across multiple chunks."""
    text_1 = "Test chunk 1."
    text_2 = "Test chunk 2."
    texts = ["Test chunk", " 1. Test chunk", " 2."]
    assert list(stream_to_sentences(texts)) == [text_1, text_2]

    async def text_gen():
        for text in texts:
            yield text

    assert [sent async for sent in async_stream_to_sentences(text_gen())] == [
        text_1,
        text_2,
    ]


def test_numbered_lists() -> None:
    """Test breaking apart numbered lists (+ removing astericks)."""
    sentences = list(
        stream_to_sentences(
            "Final Fantasy VII features several key characters who drive the narrative: "
            "1. **Cloud Strife** - The protagonist, an ex-SOLDIER mercenary and a skilled fighter. "
            "2. **Aerith Gainsborough (Aeris)** - A kindhearted flower seller with spiritual powers and deep connections to the planet's ecosystem. "
            "3. **Barret Wallace** - A leader of eco-terrorists called AVALANCHE, fighting against Shinra Corporation's exploitation of the planet. "
            "4. **Tifa Lockhart** - Cloud's childhood friend who runs a bar in Sector 7 and helps him recover from past trauma. "
            "5. **Sephiroth** - The main antagonist, an ex-SOLDIER with god-like abilities, seeking to control or destroy the planet. "
            "6. **Red XIII (aka Red 13)** - A member of a catlike race called Cetra, searching for answers about his heritage and destiny. "
            "7. **Vincent Valentine** - A brooding former Turk who lives in isolation from guilt over past failures but aids Cloud's party with his powerful abilities. "
            "8. **Cid Highwind** - The pilot of the rocket plane Highwind and a skilled engineer working on various airship projects. 9. "
            "**Shinra Employees (JENOVA Project)** - Characters like Professor Hojo, President Shinra, and Reno who play crucial roles in the plot's development. "
            "Each character brings unique skills and perspectives to the story, contributing to its rich narrative and gameplay dynamics."
        )
    )
    assert len(sentences) == 10
    assert sentences[1].startswith("2. Aerith Gainsborough")


@pytest.mark.asyncio
async def test_blank_line() -> None:
    """Test that a double newline splits a sentence."""
    text_1 = "Test sentence 1"
    text_2 = "Test sentence 2."
    text_3 = "Test sentence 3"
    text = f"{text_1}\n\n{text_2} {text_3}"
    assert list(stream_to_sentences([text])) == [text_1, text_2, text_3]

    async def text_gen():
        yield text

    assert [sent async for sent in async_stream_to_sentences(text_gen())] == [
        text_1,
        text_2,
        text_3,
    ]


@pytest.mark.asyncio
async def test_newline_punctuation() -> None:
    """Test that a newline with punctuation splits a sentence."""
    text_1 = "Test sentence 1."
    text_2 = "Test sentence 2."
    text = f"{text_1}\n{text_2}"
    assert list(stream_to_sentences([text])) == [text_1, text_2]

    async def text_gen():
        yield text

    assert [sent async for sent in async_stream_to_sentences(text_gen())] == [
        text_1,
        text_2,
    ]


@pytest.mark.parametrize(("should_pass", "text", "expected_sentences"), GOLDEN_EN_RULES)
def test_golden_rules_en(
    should_pass: bool, text: str, expected_sentences: List[str]
) -> None:
    """Test English 'golden rules'."""
    actual_sentences = list(stream_to_sentences([text]))
    if should_pass:
        assert expected_sentences == actual_sentences
    else:
        # Expected to fail
        assert expected_sentences != actual_sentences, "Expected to fail but succeeded"


def test_short_word_at_boundary() -> None:
    """Test that a short word like 'say' doesn't get misinterpreted as an abbreviation."""
    sentences = list(
        stream_to_sentences(
            [
                "This is a short message. This is a slightly longer message that takes longer to say. This is an even longer message where I'm going to keep talking for awhile."
            ]
        )
    )
    assert len(sentences) == 3


def test_chinese() -> None:
    """Test that Chinese punctuation (with quotes) work."""
    text = "“这是第一句话。”这是第二句话。"
    assert list(stream_to_sentences([text])) == ["“这是第一句话。”", "这是第二句话。"]

    # Test quotes
    text_chunks = ["“这是第一句", "话。", "”这是第二句话。"]
    assert list(stream_to_sentences(text_chunks)) == [
        "“这是第一句话。”",
        "这是第二句话。",
    ]


def test_quotes() -> None:
    text_chunks = ['"First test sentence', ".", '"', " Second test sentence."]
    assert list(stream_to_sentences(text_chunks)) == [
        '"First test sentence."',
        "Second test sentence.",
    ]
