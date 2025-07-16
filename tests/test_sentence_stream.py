"""Tests for sentence boundary detection."""

import pytest

from sentence_stream import async_stream_to_sentences, stream_to_sentences


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
