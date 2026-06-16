"""Tests for streaming behavior: chunk-invariance, edge cases, and performance."""

import time
from typing import List

import pytest

from sentence_stream import (
    SentenceBoundaryDetector,
    async_stream_to_sentences,
    stream_to_sentences,
)

from .english_golden_rules import GOLDEN_EN_RULES


def _chunks(text: str, size: int) -> List[str]:
    """Split ``text`` into fixed-size chunks."""
    return [text[i : i + size] for i in range(0, len(text), size)]


# Representative texts exercising ASCII, Chinese, blank-line, and markdown paths.
INVARIANCE_TEXTS = [text for _, text, _ in GOLDEN_EN_RULES] + [
    "Hello World. My name is Jonas.",
    "“这是第一句话。”这是第二句话。",
    "Test sentence 1\n\nTest sentence 2. Test sentence 3",
    "**Bold** text! Another *emphasized* word. Done.",
    "Mixed 中文 and English. 这是中文。Back to English.",
]


@pytest.mark.parametrize("text", INVARIANCE_TEXTS)
@pytest.mark.parametrize("size", [1, 2, 3, 5, 7])
def test_chunk_invariance(text: str, size: int) -> None:
    """Output must not depend on where chunk boundaries fall."""
    one_shot = list(stream_to_sentences([text]))
    streamed = list(stream_to_sentences(_chunks(text, size)))
    assert streamed == one_shot


@pytest.mark.parametrize("text", INVARIANCE_TEXTS)
def test_chunk_invariance_char_by_char(text: str) -> None:
    """Even single-character chunks must produce the one-shot result."""
    one_shot = list(stream_to_sentences([text]))
    streamed = list(stream_to_sentences(list(text)))
    assert streamed == one_shot


def test_empty_chunks_ignored() -> None:
    """Empty chunks interspersed in the stream are harmless."""
    chunks = ["", "Hello world.", "", " Bye now.", ""]
    assert list(stream_to_sentences(chunks)) == ["Hello world.", "Bye now."]


def test_whitespace_only_chunks() -> None:
    """Leading whitespace-only chunks don't emit spurious empty sentences."""
    chunks = ["   ", "\n\n", "  Hello there."]
    assert list(stream_to_sentences(chunks)) == ["Hello there."]


def test_no_input() -> None:
    """An empty stream yields nothing."""
    assert list(stream_to_sentences([])) == []


def test_only_whitespace() -> None:
    """Whitespace-only input yields nothing."""
    assert list(stream_to_sentences(["   \n  "])) == []


def test_finish_flushes_trailing_text() -> None:
    """Text with no terminal boundary is still emitted on finish()."""
    assert list(stream_to_sentences(["No terminal punctuation here"])) == [
        "No terminal punctuation here"
    ]


def test_finish_flushes_held_abbreviation() -> None:
    """A sentence ending in an abbreviation-like token is emitted on finish()."""
    # "Mr." is held as a possible abbreviation; finish() must still flush it.
    assert list(stream_to_sentences(["Goodbye Mr."])) == ["Goodbye Mr."]


def test_chinese_enders_split() -> None:
    """Each Chinese ender starts a new sentence."""
    assert list(stream_to_sentences(["A说。B说？C说！"])) == ["A说。", "B说？", "C说！"]


def test_chinese_ender_split_across_chunks() -> None:
    """A Chinese ender arriving in a later chunk still splits correctly."""
    assert list(stream_to_sentences(["第一句", "。第二", "句。"])) == [
        "第一句。",
        "第二句。",
    ]


@pytest.mark.asyncio
async def test_async_chunk_invariance() -> None:
    """The async entry point matches the sync result for chunked input."""
    text = "Hello World. My name is Jonas. Nice to meet you."
    expected = list(stream_to_sentences([text]))

    async def gen():
        for chunk in _chunks(text, 3):
            yield chunk

    assert [sent async for sent in async_stream_to_sentences(gen())] == expected


def test_detector_reusable_after_finish() -> None:
    """A detector can be driven again after finish() resets its state."""
    detector = SentenceBoundaryDetector()
    first = list(detector.add_chunk("One sentence. Two")) + [detector.finish()]
    assert first == ["One sentence.", "Two"]

    second = list(detector.add_chunk("Three. Four")) + [detector.finish()]
    assert second == ["Three.", "Four"]


def test_large_input_is_linear() -> None:
    """Many boundaries in a single chunk must process in roughly linear time.

    Guards against the O(n^2) rescan-from-zero regression: doubling the input
    should roughly double the time, not quadruple it. We assert a generous
    absolute bound so the test is not flaky on slow machines.
    """
    text = "This is a sentence number one. " * 8000
    start = time.perf_counter()
    count = sum(1 for _ in stream_to_sentences([text]))
    elapsed = time.perf_counter() - start

    assert count == 8000
    # The linear implementation runs in tens of milliseconds; the old quadratic
    # one took several seconds for this size. One second is a safe ceiling.
    assert elapsed < 1.0, f"took {elapsed:.3f}s; possible quadratic regression"
