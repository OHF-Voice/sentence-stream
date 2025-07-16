"""Guess the sentence boundaries in a text stream."""

from collections.abc import AsyncGenerator, AsyncIterable, Generator, Iterable

import regex as re

from .util import remove_asterisks

SENTENCE_END = r"[.!?…]|[。！？]|[؟]|[।॥]"
ABBREVIATION_RE = re.compile(r"\b\p{L}{1,3}\.$", re.UNICODE)

SENTENCE_BOUNDARY_RE = re.compile(
    rf"(.*?(?:{SENTENCE_END}+))(?=\s+[\p{{Lu}}\p{{Lt}}\p{{Lo}}]|(?:\s+\d+\.\s+))",
    re.DOTALL,
)


# -----------------------------------------------------------------------------


def stream_to_sentences(text_stream: Iterable[str]) -> Generator[str]:
    """Generate sentences from a text stream."""
    boundary_detector = SentenceBoundaryDetector()

    for text_chunk in text_stream:
        yield from boundary_detector.add_chunk(text_chunk)

    final_text = boundary_detector.finish()
    if final_text:
        yield final_text


async def async_stream_to_sentences(
    text_stream: AsyncIterable[str],
) -> AsyncGenerator[str]:
    """Generate sentences from an async text stream."""
    boundary_detector = SentenceBoundaryDetector()

    async for text_chunk in text_stream:
        for sentence in boundary_detector.add_chunk(text_chunk):
            yield sentence

    final_text = boundary_detector.finish()
    if final_text:
        yield final_text


# -----------------------------------------------------------------------------


class SentenceBoundaryDetector:
    """Detect sentence boundaries from a text stream."""

    def __init__(self) -> None:
        self.remaining_text = ""
        self.current_sentence = ""

    def add_chunk(self, chunk: str) -> Iterable[str]:
        """Add text chunk to stream and yield all detected sentences."""
        self.remaining_text += chunk
        while self.remaining_text:
            match = SENTENCE_BOUNDARY_RE.search(self.remaining_text)
            if not match:
                break

            match_text = match.group(0)

            if not self.current_sentence:
                self.current_sentence = match_text
            elif ABBREVIATION_RE.search(self.current_sentence[-5:]):
                self.current_sentence += match_text
            else:
                yield remove_asterisks(self.current_sentence.strip())
                self.current_sentence = match_text

            if not ABBREVIATION_RE.search(self.current_sentence[-5:]):
                yield remove_asterisks(self.current_sentence.strip())
                self.current_sentence = ""

            self.remaining_text = self.remaining_text[match.end() :]

    def finish(self) -> str:
        """End text stream and yield final sentence."""
        text = (self.current_sentence + self.remaining_text).strip()
        self.remaining_text = ""
        self.current_sentence = ""

        return remove_asterisks(text)
