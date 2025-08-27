"""Guess the sentence boundaries in a text stream."""

from collections.abc import AsyncGenerator, AsyncIterable, Generator, Iterable

import regex as re

from .util import remove_asterisks

SENTENCE_END = r"[.!?…]|[。！？]|[؟]|[।॥]"
ABBREVIATION_RE = re.compile(r"\b\p{Lu}(?:\p{L}{1,2})?\.$", re.UNICODE)

SENTENCE_BOUNDARY_RE = re.compile(
    rf"(?:{SENTENCE_END}+)(?=\s+[\p{{Lu}}\p{{Lt}}\p{{Lo}}]|(?:\s+\d+[.)]{{1,2}}\s+))",
    re.DOTALL,
)
BLANK_LINES_RE = re.compile(r"(?:\r?\n){2,}")


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
            match_blank_lines = BLANK_LINES_RE.search(self.remaining_text)
            match_punctuation = SENTENCE_BOUNDARY_RE.search(self.remaining_text)
            if match_blank_lines and match_punctuation:
                if match_blank_lines.start() < match_punctuation.start():
                    first_match = match_blank_lines
                else:
                    first_match = match_punctuation
            elif match_blank_lines:
                first_match = match_blank_lines
            elif match_punctuation:
                first_match = match_punctuation
            else:
                break

            match_text = self.remaining_text[: first_match.start() + 1]
            match_end = first_match.end()

            if not self.current_sentence:
                if ABBREVIATION_RE.search(match_text[-5:]):
                    # We can't know yet if this is a sentence boundary or an abbreviation
                    self.current_sentence = match_text
                elif output_text := remove_asterisks(match_text.strip()):
                    yield output_text
            elif ABBREVIATION_RE.search(self.current_sentence[-5:]):
                self.current_sentence += match_text
            else:
                if output_text := remove_asterisks(self.current_sentence.strip()):
                    yield output_text
                self.current_sentence = match_text

            if not ABBREVIATION_RE.search(self.current_sentence[-5:]):
                if output_text := remove_asterisks(self.current_sentence.strip()):
                    yield output_text
                self.current_sentence = ""

            self.remaining_text = self.remaining_text[match_end:]

    def finish(self) -> str:
        """End text stream and yield final sentence."""
        text = (self.current_sentence + self.remaining_text).strip()
        self.remaining_text = ""
        self.current_sentence = ""

        return remove_asterisks(text)
