"""Guess the sentence boundaries in a text stream."""

from collections.abc import AsyncGenerator, AsyncIterable, Generator, Iterable

import regex as re

from .util import remove_asterisks

SENTENCE_END = r"[.!?…]|[؟]|[।॥]"
ABBREVIATION_RE = re.compile(r"\b\p{Lu}(?:\p{L}{1,2})?\.$", re.UNICODE)

# ASCII / Latin sentence boundaries
ASCII_CLOSERS = r"['\"\)\]\}\u2019\u201d»]*"  # ' " ) ] } ’ ” »
SENTENCE_BOUNDARY_RE = re.compile(
    rf"(?:{SENTENCE_END}+){ASCII_CLOSERS}"
    rf"(?=\s+[\p{{Lu}}\p{{Lt}}\p{{Lo}}]|(?:\s+\d+[.)]{{1,2}}\s+))",
    re.DOTALL,
)

# Chinese sentence boundaries (enders + trailing closers)
ZH_CLOSERS = "”’」』）》】〕〉）"
ZH_ENDERS = "。！？"
SENTENCE_BOUNDARY_ZH_RE = re.compile(rf"(?:[{ZH_ENDERS}]|……|…)+[{ZH_CLOSERS}]*")

BLANK_LINES_RE = re.compile(r"(?:\r?\n){2,}")


# -----------------------------------------------------------------------------


def stream_to_sentences(text_stream: Iterable[str]) -> Generator[str, None, None]:
    """Generate sentences from a text stream."""
    boundary_detector = SentenceBoundaryDetector()

    for text_chunk in text_stream:
        yield from boundary_detector.add_chunk(text_chunk)

    final_text = boundary_detector.finish()
    if final_text:
        yield final_text


async def async_stream_to_sentences(
    text_stream: AsyncIterable[str],
) -> AsyncGenerator[str, None]:
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
            match_punctuation_zh = SENTENCE_BOUNDARY_ZH_RE.search(self.remaining_text)
            match_punctuation_ascii = SENTENCE_BOUNDARY_RE.search(self.remaining_text)

            # Choose earliest punctuation (Chinese vs ASCII)
            if match_punctuation_zh and match_punctuation_ascii:
                match_punctuation = (
                    match_punctuation_zh
                    if match_punctuation_zh.start() < match_punctuation_ascii.start()
                    else match_punctuation_ascii
                )
            else:
                match_punctuation = match_punctuation_zh or match_punctuation_ascii

            # Choose earliest boundary overall (blank lines vs punctuation)
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

            # If this is a Chinese sentence boundary *at the end of the buffer*,
            # do not consume it yet. Wait for the next chunk so we can pick up
            # any following closers (e.g., ”, 》, ）) and following text.
            if first_match is match_punctuation_zh and first_match.end() == len(
                self.remaining_text
            ):
                break

            match_end = first_match.end()
            match_text = self.remaining_text[:match_end]

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

            # If the current sentence no longer looks like an abbreviation, flush it.
            if self.current_sentence and not ABBREVIATION_RE.search(
                self.current_sentence[-5:]
            ):
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
