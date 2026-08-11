"""Guess the sentence boundaries in a text stream."""

from collections.abc import AsyncGenerator, AsyncIterable, Generator, Iterable

import regex as re

from .util import remove_asterisks

SENTENCE_END = (
    r"[.!?…]"  # ASCII / Latin
    r"|[؟۔]"  # Arabic question mark, Urdu full stop
    r"|[।॥]"  # Devanagari danda, double danda
    r"|[។៕]"  # Khmer khan, bariyoosan
    r"|[။]"  # Myanmar section
    r"|[།༎]"  # Tibetan shad, double shad
    r"|[።]"  # Ethiopic full stop
    r"|[։]"  # Armenian full stop
    r"|[;]"  # Greek question mark
    # Greek is normally typed with an ASCII semicolon in place of U+037E, so a
    # semicolon only ends a sentence when it directly follows a Greek letter.
    # Without that guard every English semicolon would become a boundary.
    r"|(?<=\p{Greek});"
)
ABBREVIATION_RE = re.compile(r"\b\p{Lu}(?:\p{L}{1,2})?\.$", re.UNICODE)

# ASCII / Latin sentence boundaries
#
# ‘ and “ close a quotation in German („Hallo.“), which is where English
# opens one -- the same characters therefore appear in ASCII_OPENERS below.
# Position disambiguates them: a closer sits against the punctuation, an opener
# comes after whitespace.
ASCII_CLOSERS = r"['\"\)\]\}\u2018\u2019\u201c\u201d»]*"  # ' " ) ] } ‘ ’ “ ” »

# A sentence may open with punctuation before its first letter: inverted marks
# (¿Cómo estás?) or quotes ("Hello", «Bonjour», „Hallo“). Openers are matched
# between the whitespace and the first letter, so they can't be confused with
# closers -- a quote sitting directly against the preceding punctuation is
# consumed by ASCII_CLOSERS instead. French sets its guillemets off with a space
# ("« Bonjour"), hence the whitespace allowed after the opener.
#
# Brackets are deliberately absent. They open a sentence ("Done. (See below.)")
# just as often as they open a parenthetical that continues one, and treating
# them as openers splits a trailing citation off its quotation. So is ``*``:
# numbered markdown lists ("2. **Item**") rely on an asterisk not opening a
# sentence.
ASCII_OPENERS = r"[¿¡«‹„“‚‘\"']*"  # ¿ ¡ « ‹ „ “ ‚ ‘ " '
SENTENCE_BOUNDARY_RE = re.compile(
    rf"(?:{SENTENCE_END}+){ASCII_CLOSERS}"
    rf"(?=\s+{ASCII_OPENERS}\s*[\p{{Lu}}\p{{Lt}}\p{{Lo}}]"
    rf"|(?:\s+\d+[.)]{{1,2}}\s+))",
    re.DOTALL,
)

# CJK sentence boundaries (enders + trailing closers). Chinese and Japanese
# share the same terminators, so one pattern covers both.
CJK_CLOSERS = "”’」』｣）》】〕〉〞〟" + r")\]\}\"'»"
CJK_ENDERS = "。！？｡"

# A closing quote followed by と/って is the Japanese quotative particle, not a
# sentence break ("「行こう！」と言った。" is one sentence), so refuse the
# boundary there. The closers are matched possessively and the bare-ender
# branch requires that no closer follows, otherwise the pattern could backtrack
# into a shorter match that splits *before* the closer. A bare ender followed by
# と is still a boundary, since plenty of sentences begin with と ("ところで…").
SENTENCE_BOUNDARY_CJK_RE = re.compile(
    rf"(?:[{CJK_ENDERS}]|…)++(?:[{CJK_CLOSERS}]++(?![とっ])|(?![{CJK_CLOSERS}]))"
)

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
        text = self.remaining_text
        text_len = len(text)

        # Walk the buffer with a cursor instead of re-slicing it every
        # iteration, and cache each pattern's next match so we don't rescan the
        # whole buffer for every boundary. Once a pattern returns None there is
        # no further match in this buffer, so it is never searched again.
        consumed = 0
        match_blank_lines = BLANK_LINES_RE.search(text, consumed)
        match_punctuation_cjk = SENTENCE_BOUNDARY_CJK_RE.search(text, consumed)
        match_punctuation_ascii = SENTENCE_BOUNDARY_RE.search(text, consumed)

        while consumed < text_len:
            # Refresh a cached match only when the cursor has advanced past it;
            # an as-yet-unconsumed match is still the earliest one.
            if match_blank_lines is not None and match_blank_lines.start() < consumed:
                match_blank_lines = BLANK_LINES_RE.search(text, consumed)
            if (
                match_punctuation_cjk is not None
                and match_punctuation_cjk.start() < consumed
            ):
                match_punctuation_cjk = SENTENCE_BOUNDARY_CJK_RE.search(text, consumed)
            if (
                match_punctuation_ascii is not None
                and match_punctuation_ascii.start() < consumed
            ):
                match_punctuation_ascii = SENTENCE_BOUNDARY_RE.search(text, consumed)

            # Choose earliest punctuation (CJK vs ASCII)
            if match_punctuation_cjk and match_punctuation_ascii:
                match_punctuation = (
                    match_punctuation_cjk
                    if match_punctuation_cjk.start() < match_punctuation_ascii.start()
                    else match_punctuation_ascii
                )
            else:
                match_punctuation = match_punctuation_cjk or match_punctuation_ascii

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

            # If this is a CJK sentence boundary *at the end of the buffer*,
            # do not consume it yet. Wait for the next chunk so we can pick up
            # any following closers (e.g., ”, 》, ）) and following text.
            if first_match is match_punctuation_cjk and first_match.end() == text_len:
                break

            match_end = first_match.end()
            match_text = text[consumed:match_end]

            if self.current_sentence:
                # Invariant: when current_sentence is non-empty here it always
                # ends in a possible abbreviation, so keep accumulating until
                # the flush check below proves otherwise.
                self.current_sentence += match_text
            elif ABBREVIATION_RE.search(match_text[-5:]):
                # We can't know yet if this is a sentence boundary or an abbreviation
                self.current_sentence = match_text
            elif output_text := remove_asterisks(match_text.strip()):
                yield output_text

            # If the current sentence no longer looks like an abbreviation, flush it.
            if self.current_sentence and not ABBREVIATION_RE.search(
                self.current_sentence[-5:]
            ):
                if output_text := remove_asterisks(self.current_sentence.strip()):
                    yield output_text
                self.current_sentence = ""

            consumed = match_end

        self.remaining_text = text[consumed:]

    def finish(self) -> str:
        """End text stream and yield final sentence."""
        text = (self.current_sentence + self.remaining_text).strip()
        self.remaining_text = ""
        self.current_sentence = ""
        return remove_asterisks(text)
