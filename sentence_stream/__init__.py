"""Guess the sentence boundaries in a text stream."""

from .sentence_stream import async_stream_to_sentences, stream_to_sentences

__all__ = ["async_stream_to_sentences", "stream_to_sentences"]
