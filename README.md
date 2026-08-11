# Sentence Stream

A small sentence splitter for text streams.

Sentences come out as soon as their boundary is certain, so a stream of text
chunks — from an LLM, say — can be handed to a text-to-speech engine a sentence
at a time instead of waiting for the whole response.

## Install

``` sh
pip install sentence-stream
```

## Example

``` python
from sentence_stream import stream_to_sentences

text_chunks = [
    "Text chunks that a",
    "re not on",
    " word or se",
    "ntence boundarie",
    "s. But, they w",
    "ill sti",
    "ll get sp",
    "lit right",
    "!!! Goo",
    "d",
]

assert list(stream_to_sentences(text_chunks)) == [
    "Text chunks that are not on word or sentence boundaries.",
    "But, they will still get split right!!!",
    "Good",
]
```

Where the chunk boundaries fall never changes the result: the same text split
into different chunks always produces the same sentences.

For async streams, use `async_stream_to_sentences`:

``` python
from sentence_stream import async_stream_to_sentences

async def main(text_stream):
    async for sentence in async_stream_to_sentences(text_stream):
        print(sentence)
```

## Pushing chunks yourself

`SentenceBoundaryDetector` is the same logic without the iterator, for when text
arrives by callback rather than from something you can loop over. `add_chunk`
returns the sentences that are now complete, and `finish` returns whatever text
is left over — an empty string if there is none.

``` python
from sentence_stream import SentenceBoundaryDetector

detector = SentenceBoundaryDetector()

for sentence in detector.add_chunk("Hello world. Goodbye"):
    print(sentence)  # Hello world.

if final_sentence := detector.finish():
    print(final_sentence)  # Goodbye
```

A detector resets itself in `finish`, so it can be reused for the next stream.

## What counts as a boundary

- Terminators followed by whitespace and a capital letter: `.` `!` `?` `…`
- CJK terminators, which need no whitespace after them: `。` `！` `？` `｡`,
  along with trailing closers such as `」` `』` `）` `》`
- Terminators for other scripts: `؟` (Arabic), `۔` (Urdu), `।` `॥`
  (Devanagari), `។` `៕` (Khmer), `။` (Myanmar), `།` `༎` (Tibetan), `።`
  (Ethiopic), `։` (Armenian), and `;` in Greek
- A blank line

A sentence may open with punctuation before its first letter — `¿` `¡` `«` `„`
and quotation marks — and may end with closing quotes or brackets.

Abbreviations are held rather than split on: initials (`Jonas E. Smith`), dotted
acronyms (`U.S.`), and a list of known words (`Mr.`, `Mt.`, `etc.`).

Markdown emphasis is stripped from the output, so `**Bold**` is read as `Bold`.
Text that only resembles markup is left alone, including `2*3*4`.

## Known limitations

This is a heuristic splitter, not a parser. It errs toward leaving a sentence
whole, since an over-eager split is more noticeable when read aloud than a long
sentence.

- **Thai and Lao** are never split. Neither script has a sentence terminator —
  sentences are separated with a space — so there is nothing to key on.
- **Georgian** is never split. The Mkhedruli script has no uppercase, and a
  boundary needs a capital letter after the terminator.
- **List markers** are split off as their own sentence: `1. The first item`
  becomes `1.` and `The first item`, unless the item is emphasized.
- **A sentence-ending abbreviation** stays joined to the sentence after it:
  `I live in the U.S. How about you?` comes out whole, because the same
  `U.S.` also appears mid-sentence in `the U.S. Government`.
- **Spaced ellipses** (`. . .`) are treated as a boundary.

The `tests/english_golden_rules.py` suite records which of pySBD's golden rules
pass and pins the output for those that do not.
