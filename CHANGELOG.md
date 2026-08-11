# Changelog

## 1.4.0

Languages:

- Handle Japanese: the quotative particle after a closing bracket no longer
  splits a sentence ("「行こう！」と言った。"), half-width `｡` and `｣` are
  recognized, and `〞〟` are treated as closers
- Handle sentence terminators for Urdu, Khmer, Myanmar, Tibetan, Ethiopic,
  Armenian and Greek. A semicolon only ends a sentence in Greek, so English
  semicolons are unaffected
- Split sentences that open with punctuation: `¿`, `¡`, `«`, `„` and quotes

Fixes:

- `SentenceBoundaryDetector.add_chunk` returns a list instead of being a
  generator. Ignoring the return value used to discard the chunk, and
  abandoning the iteration part-way used to emit text twice
- Streaming no longer degrades to O(n^2) when boundaries are rare, which
  affected long unpunctuated text and scripts with no terminator at all, such
  as Thai. 40k characters in 8-character chunks went from 1231ms to 10ms
- A short capitalized word no longer looks like an abbreviation, so
  "Turn on the TV. Then sit down." splits. Abbreviations are now recognized
  from initials, dotted acronyms and a known-word list
- Markdown stripping leaves text that only resembles markup alone:
  "2*3*4 = 24." was being rewritten to "234 = 24."
- Removing a bullet's asterisks no longer swallows a preceding blank line

## 1.3.0

- Handle Chinese punctuation (without whitespace)
- Handle punctuation inside quotes
- Add py.typed file

## 1.2.1

- Relax regex version

## 1.2.0

- Fixes for abbreviations

## 1.1.0

- Split sentences on double newlines

## 1.0.0

- Initial release
