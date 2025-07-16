# Sentence Stream

A small sentence splitter for text streams.

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

For async streams, use `async_stream_to_sentences`.
