"""Tests for streaming behavior: chunk-invariance, edge cases, and performance."""

import random
import time
from typing import List

import pytest

from sentence_stream import SentenceBoundaryDetector, async_stream_to_sentences
from sentence_stream import sentence_stream as sentence_stream_module
from sentence_stream import stream_to_sentences

from .english_golden_rules import GOLDEN_EN_RULES


def _chunks(text: str, size: int) -> List[str]:
    """Split ``text`` into fixed-size chunks."""
    return [text[i : i + size] for i in range(0, len(text), size)]


# Representative texts exercising ASCII, Chinese, Japanese, blank-line, and
# markdown paths.
INVARIANCE_TEXTS = [text for _, text, _ in GOLDEN_EN_RULES] + [
    "Hello World. My name is Jonas.",
    "“这是第一句话。”这是第二句话。",
    "Test sentence 1\n\nTest sentence 2. Test sentence 3",
    "**Bold** text! Another *emphasized* word. Done.",
    "Mixed 中文 and English. 这是中文。Back to English.",
    "「これは最初の文です。」これは二番目の文です。",
    "「行こう！」と言った。それから出発した。",
    "えっ！？本当ですか？そうですね……はい。",
    "Mixed 日本語 and English. これは日本語です。Back to English.",
    "Τι κάνεις; Είμαι καλά. Χαίρω πολύ.",
    "I came; I saw; I conquered. Then I left.",
    "یہ پہلا جملہ ہے۔ یہ دوسرا جملہ ہے۔",
    "Սա առաջին նախադասությունն է։ Սա երկրորդն է։",
    "Hola. ¿Cómo estás? ¡Muy bien!",
    'He left. "Hello there." Then silence.',
    "Er sagte. „Hallo.“ Und dann.",
    "The result. (See below.) Done.",
    "Wait…“ Yes it is.",
    "։ ¡\n\nと….",
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


@pytest.mark.parametrize("text", INVARIANCE_TEXTS)
def test_bare_string_matches_single_chunk(text: str) -> None:
    """A whole string is accepted, and means one chunk rather than one per character.

    A str is itself an Iterable[str], so passing one used to type-check and work
    while quietly streaming character by character.
    """
    assert list(stream_to_sentences(text)) == list(stream_to_sentences([text]))


def test_bare_string_is_not_iterated_per_character(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The whole string reaches the detector in one go, not a character at a time."""
    seen: List[str] = []

    class Recorder(SentenceBoundaryDetector):
        """Records the chunks it is handed."""

        def add_chunk(self, chunk: str) -> List[str]:
            seen.append(chunk)
            return super().add_chunk(chunk)

    monkeypatch.setattr(sentence_stream_module, "SentenceBoundaryDetector", Recorder)

    text = "Hello world. Goodbye world."
    assert list(sentence_stream_module.stream_to_sentences(text)) == [
        "Hello world.",
        "Goodbye world.",
    ]
    assert seen == [text]


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
    # pylint: disable=use-implicit-booleaness-not-comparison
    assert list(stream_to_sentences([])) == []


def test_only_whitespace() -> None:
    """Whitespace-only input yields nothing."""
    # pylint: disable=use-implicit-booleaness-not-comparison
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


# Fragments spanning every code path: Latin, CJK, script terminators, quotes and
# inverted marks, markdown, blank lines, abbreviations and list numbering.
_FUZZ_PIECES = (
    list("abcdefgHIJK ")
    + [".", "!", "?", "…", "。", "！", "？", "、", ",", ";", "\n", "\n\n", "  "]
    + ['"', "'", "“", "”", "„", "«", "»", "¿", "¡", "「", "」", "（", "）"]
    + ["*", "**", "と", "って", "あ", "中", "文"]
    + ["؟", "।", "۔", "។", "།", "።", "։", "Α", "α", "ς"]
    + ["(", ")", "Mr.", "U.S.", "TV.", "5", "2."]
)


def _normalized(text: str) -> str:
    """Strip everything the splitter is allowed to drop: whitespace and markup."""
    return "".join(text.split()).replace("*", "")


@pytest.mark.parametrize("seed", (1, 7, 42, 1234))
def test_fuzz_chunk_invariance_and_preservation(seed: int) -> None:
    """Random texts must split the same however they are chunked, losing nothing.

    Both properties are load-bearing and neither is obvious from the patterns:
    this is what caught a CJK boundary committing before a competing ASCII match
    could complete, and an opener whose lookahead reached over a blank line.
    """
    rng = random.Random(seed)
    for _ in range(500):
        text = "".join(rng.choice(_FUZZ_PIECES) for _ in range(rng.randint(1, 30)))
        one_shot = list(stream_to_sentences([text]))

        chunkings = [list(text), _chunks(text, 3)]
        if len(text) > 1:
            split_at = rng.randint(1, len(text) - 1)
            chunkings.append([text[:split_at], text[split_at:]])
        for chunking in chunkings:
            assert (
                list(stream_to_sentences(chunking)) == one_shot
            ), f"chunking changed the split of {text!r}"

        assert _normalized("".join(one_shot)) == _normalized(
            text
        ), f"text lost or duplicated for {text!r}"


def test_add_chunk_is_eager() -> None:
    """add_chunk must apply the chunk even if the caller ignores the result.

    As a generator its body never ran until iterated, so discarding the return
    value silently dropped the chunk.
    """
    detector = SentenceBoundaryDetector()
    detector.add_chunk("Hello world. Goodbye world.")  # result deliberately unused
    assert detector.finish() == "Goodbye world."


def test_add_chunk_returns_a_concrete_sequence() -> None:
    """add_chunk returns a real sequence, not a lazy iterator."""
    detector = SentenceBoundaryDetector()
    result = detector.add_chunk("One sentence here. Two sentences here.")
    assert isinstance(result, list)
    # Re-iterable, unlike a generator.
    assert list(result) == list(result) == ["One sentence here."]


def test_partial_consumption_does_not_duplicate() -> None:
    """Abandoning the returned sentences must not corrupt the buffer.

    While add_chunk was a generator, breaking out of the loop skipped the final
    buffer update, so already-emitted text was emitted again by finish().
    """
    detector = SentenceBoundaryDetector()
    for sentence in detector.add_chunk("Alpha beta. Gamma delta. Epsilon zeta."):
        assert sentence == "Alpha beta."
        break
    assert detector.finish() == "Epsilon zeta."


def test_consumer_exception_does_not_duplicate() -> None:
    """An exception while handling sentences must not corrupt the buffer."""
    detector = SentenceBoundaryDetector()
    with pytest.raises(RuntimeError):
        for _sentence in detector.add_chunk("Alpha beta. Gamma delta. Epsilon zeta."):
            raise RuntimeError("consumer failed")
    assert detector.finish() == "Epsilon zeta."


def test_boundary_free_stream_is_linear() -> None:
    """Streaming text with no boundaries must not be quadratic in buffer length.

    Every chunk used to restart all three searches at position 0 of the whole
    accumulated buffer, so a boundary-free stream cost O(n^2): this input took
    over a second. Thai and Lao hit it unconditionally, having no sentence
    terminator for the buffer to drain on.
    """
    chunks = _chunks("word " * 8000, 8)  # 40k chars, no boundary anywhere
    start = time.perf_counter()
    sentences = list(stream_to_sentences(chunks))
    elapsed = time.perf_counter() - start

    assert sentences == [("word " * 8000).strip()]
    assert elapsed < 1.0, f"took {elapsed:.3f}s; possible quadratic regression"


def test_settled_text_is_reassembled() -> None:
    """A sentence longer than one chunk is rejoined from the settled buffer.

    Settled text is filed away from the search buffer as it accumulates, so the
    join has to put it back in front of the sentence that completes it.
    """
    long_sentence = "word " * 2000 + "end."
    text = long_sentence + " Next one."
    assert list(stream_to_sentences(_chunks(text, 8))) == [
        long_sentence,
        "Next one.",
    ]


def test_lookbehind_survives_chunk_boundary() -> None:
    """A Greek question mark still splits when its letter arrives in an earlier chunk.

    The boundary is gated on a lookbehind, which fails if the preceding letter
    has already been filed away from the search buffer.
    """
    text = "Τι κάνεις; Είμαι καλά."
    for size in (1, 2, 3, 5):
        assert list(stream_to_sentences(_chunks(text, size))) == [
            "Τι κάνεις;",
            "Είμαι καλά.",
        ]


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
