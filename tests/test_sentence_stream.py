"""Tests for sentence boundary detection."""

from typing import List

import pytest

from sentence_stream import async_stream_to_sentences, stream_to_sentences

from .english_golden_rules import GOLDEN_EN_RULES


@pytest.mark.asyncio
async def test_one_chunk() -> None:
    """Test that a single text chunk produces a single sentence."""
    text = "Test chunk"
    assert list(stream_to_sentences([text])) == [text]

    async def text_gen():
        yield text

    assert [sent async for sent in async_stream_to_sentences(text_gen())] == [text]


@pytest.mark.parametrize("punctuation", (".", "?", "!", "!?"))
@pytest.mark.asyncio
async def test_one_chunk_with_punctuation(punctuation: str) -> None:
    """Test that punctuation splits sentences in a single chunk."""
    text_1 = f"Test chunk 1{punctuation}"
    text_2 = "Test chunk 2"
    text = f"{text_1} {text_2}"

    assert list(stream_to_sentences([text])) == [text_1, text_2]

    async def text_gen():
        yield text

    assert [sent async for sent in async_stream_to_sentences(text_gen())] == [
        text_1,
        text_2,
    ]


@pytest.mark.asyncio
async def test_multiple_chunks() -> None:
    """Test sentence splitting across multiple chunks."""
    text_1 = "Test chunk 1."
    text_2 = "Test chunk 2."
    texts = ["Test chunk", " 1. Test chunk", " 2."]
    assert list(stream_to_sentences(texts)) == [text_1, text_2]

    async def text_gen():
        for text in texts:
            yield text

    assert [sent async for sent in async_stream_to_sentences(text_gen())] == [
        text_1,
        text_2,
    ]


def test_numbered_lists() -> None:
    """Test breaking apart numbered lists (+ removing astericks)."""
    sentences = list(
        stream_to_sentences(
            "Final Fantasy VII features several key characters who drive the narrative: "
            "1. **Cloud Strife** - The protagonist, an ex-SOLDIER mercenary and a skilled fighter. "
            "2. **Aerith Gainsborough (Aeris)** - A kindhearted flower seller with spiritual powers and deep connections to the planet's ecosystem. "
            "3. **Barret Wallace** - A leader of eco-terrorists called AVALANCHE, fighting against Shinra Corporation's exploitation of the planet. "
            "4. **Tifa Lockhart** - Cloud's childhood friend who runs a bar in Sector 7 and helps him recover from past trauma. "
            "5. **Sephiroth** - The main antagonist, an ex-SOLDIER with god-like abilities, seeking to control or destroy the planet. "
            "6. **Red XIII (aka Red 13)** - A member of a catlike race called Cetra, searching for answers about his heritage and destiny. "
            "7. **Vincent Valentine** - A brooding former Turk who lives in isolation from guilt over past failures but aids Cloud's party with his powerful abilities. "
            "8. **Cid Highwind** - The pilot of the rocket plane Highwind and a skilled engineer working on various airship projects. 9. "
            "**Shinra Employees (JENOVA Project)** - Characters like Professor Hojo, President Shinra, and Reno who play crucial roles in the plot's development. "
            "Each character brings unique skills and perspectives to the story, contributing to its rich narrative and gameplay dynamics."
        )
    )
    assert len(sentences) == 10
    assert sentences[1].startswith("2. Aerith Gainsborough")


@pytest.mark.asyncio
async def test_blank_line() -> None:
    """Test that a double newline splits a sentence."""
    text_1 = "Test sentence 1"
    text_2 = "Test sentence 2."
    text_3 = "Test sentence 3"
    text = f"{text_1}\n\n{text_2} {text_3}"
    assert list(stream_to_sentences([text])) == [text_1, text_2, text_3]

    async def text_gen():
        yield text

    assert [sent async for sent in async_stream_to_sentences(text_gen())] == [
        text_1,
        text_2,
        text_3,
    ]


@pytest.mark.asyncio
async def test_newline_punctuation() -> None:
    """Test that a newline with punctuation splits a sentence."""
    text_1 = "Test sentence 1."
    text_2 = "Test sentence 2."
    text = f"{text_1}\n{text_2}"
    assert list(stream_to_sentences([text])) == [text_1, text_2]

    async def text_gen():
        yield text

    assert [sent async for sent in async_stream_to_sentences(text_gen())] == [
        text_1,
        text_2,
    ]


@pytest.mark.parametrize(("should_pass", "text", "expected_sentences"), GOLDEN_EN_RULES)
def test_golden_rules_en(
    should_pass: bool, text: str, expected_sentences: List[str]
) -> None:
    """Test English 'golden rules'."""
    actual_sentences = list(stream_to_sentences([text]))
    if should_pass:
        assert expected_sentences == actual_sentences
    else:
        # Expected to fail
        assert expected_sentences != actual_sentences, "Expected to fail but succeeded"


def test_short_word_at_boundary() -> None:
    """Test that a short word like 'say' doesn't get misinterpreted as an abbreviation."""
    sentences = list(
        stream_to_sentences(
            [
                "This is a short message. This is a slightly longer message that takes longer to say. This is an even longer message where I'm going to keep talking for awhile."
            ]
        )
    )
    assert len(sentences) == 3


def test_chinese() -> None:
    """Test that Chinese punctuation (with quotes) work."""
    text = "“这是第一句话。”这是第二句话。"
    assert list(stream_to_sentences([text])) == ["“这是第一句话。”", "这是第二句话。"]

    # Test quotes
    text_chunks = ["“这是第一句", "话。", "”这是第二句话。"]
    assert list(stream_to_sentences(text_chunks)) == [
        "“这是第一句话。”",
        "这是第二句话。",
    ]


def test_japanese() -> None:
    """Test that Japanese punctuation (with corner brackets) works."""
    text = "「これは最初の文です。」これは二番目の文です。"
    assert list(stream_to_sentences([text])) == [
        "「これは最初の文です。」",
        "これは二番目の文です。",
    ]

    # Test corner brackets arriving in a later chunk
    text_chunks = ["「これは最初", "の文です。", "」これは二番目の文です。"]
    assert list(stream_to_sentences(text_chunks)) == [
        "「これは最初の文です。」",
        "これは二番目の文です。",
    ]


@pytest.mark.parametrize(
    ("text", "expected_sentences"),
    (
        # Full-width enders
        ("これは何ですか？わかりません。", ["これは何ですか？", "わかりません。"]),
        ("えっ！？本当ですか？", ["えっ！？", "本当ですか？"]),
        ("そうですね……わかりました。", ["そうですね……", "わかりました。"]),
        # Half-width ideographic full stop
        ("最初の文です｡二番目の文です｡", ["最初の文です｡", "二番目の文です｡"]),
        # Full-width parentheses as closers
        ("彼は来た（たぶん）。次の文。", ["彼は来た（たぶん）。", "次の文。"]),
        # Double angle brackets as closers
        ("《引用です。》次の文です。", ["《引用です。》", "次の文です。"]),
    ),
)
def test_japanese_enders(text: str, expected_sentences: List[str]) -> None:
    """Test Japanese enders and closers not covered by the Chinese tests."""
    assert list(stream_to_sentences([text])) == expected_sentences


@pytest.mark.parametrize(
    ("text", "expected_sentences"),
    (
        (
            "「行こう！」と言った。次の文です。",
            ["「行こう！」と言った。", "次の文です。"],
        ),
        ("彼は「はい。」と答えた。終わり。", ["彼は「はい。」と答えた。", "終わり。"]),
        ("「多分ね」って言ってた。", ["「多分ね」って言ってた。"]),
        # A *bare* ender followed by と is still a boundary, since sentences do
        # start with と.
        ("これです。ところで、次の話。", ["これです。", "ところで、次の話。"]),
    ),
)
def test_japanese_quotative(text: str, expected_sentences: List[str]) -> None:
    """Test that the quotative particle after a closer doesn't split a sentence."""
    assert list(stream_to_sentences([text])) == expected_sentences


@pytest.mark.parametrize(
    ("language", "text", "expected_sentences"),
    (
        (
            "urdu",
            "یہ پہلا جملہ ہے۔ یہ دوسرا جملہ ہے۔",
            ["یہ پہلا جملہ ہے۔", "یہ دوسرا جملہ ہے۔"],
        ),
        (
            "khmer",
            "នេះជាប្រយោគទីមួយ។ នេះជាប្រយោគទីពីរ។",
            ["នេះជាប្រយោគទីមួយ។", "នេះជាប្រយោគទីពីរ។"],
        ),
        (
            "khmer-bariyoosan",
            "នេះជាប្រយោគទីមួយ៕ នេះជាប្រយោគទីពីរ៕",
            ["នេះជាប្រយោគទីមួយ៕", "នេះជាប្រយោគទីពីរ៕"],
        ),
        (
            "burmese",
            "ဤသည်ပထမစာကြောင်းဖြစ်သည်။ ဤသည်ဒုတိယဖြစ်သည်။",
            ["ဤသည်ပထမစာကြောင်းဖြစ်သည်။", "ဤသည်ဒုတိယဖြစ်သည်။"],
        ),
        (
            "tibetan",
            "འདི་དང་པོ་ཡིན། འདི་གཉིས་པ་ཡིན།",
            ["འདི་དང་པོ་ཡིན།", "འདི་གཉིས་པ་ཡིན།"],
        ),
        (
            "ethiopic",
            "ይህ የመጀመሪያው ዓረፍተ ነገር ነው። ይህ ሁለተኛው ነው።",
            ["ይህ የመጀመሪያው ዓረፍተ ነገር ነው።", "ይህ ሁለተኛው ነው።"],
        ),
        (
            "armenian",
            "Սա առաջին նախադասությունն է։ Սա երկրորդն է։",
            ["Սա առաջին նախադասությունն է։", "Սա երկրորդն է։"],
        ),
        # Greek written with an ASCII semicolon as the question mark...
        ("greek", "Τι κάνεις; Είμαι καλά.", ["Τι κάνεις;", "Είμαι καλά."]),
        # ...and with the "proper" U+037E, which looks identical.
        ("greek-u037e", "Τι κάνεις; Είμαι καλά.", ["Τι κάνεις;", "Είμαι καλά."]),
    ),
)
def test_script_specific_terminators(
    language: str, text: str, expected_sentences: List[str]
) -> None:
    """Test full stops and question marks outside ASCII and CJK."""
    assert list(stream_to_sentences([text])) == expected_sentences


@pytest.mark.parametrize(
    ("text", "expected_sentences"),
    (
        ("I came; I saw; I conquered.", ["I came; I saw; I conquered."]),
        ("One thing; Another thing; A third.", ["One thing; Another thing; A third."]),
        ("int x = 1; Foo y = bar; Done.", ["int x = 1; Foo y = bar; Done."]),
        # Spanish: the semicolons hold, only the period splits.
        ("Vino; vio; venció. Fin.", ["Vino; vio; venció.", "Fin."]),
    ),
)
def test_semicolon_is_not_a_terminator(
    text: str, expected_sentences: List[str]
) -> None:
    """A semicolon only ends a sentence in Greek, never in a Latin script.

    The Greek question mark is normally typed as an ASCII semicolon, so the
    boundary is gated on a preceding Greek letter. Without that guard, each of
    these would split at every semicolon.
    """
    assert list(stream_to_sentences([text])) == expected_sentences


@pytest.mark.parametrize(
    ("text", "expected_sentences"),
    (
        # Spanish inverted marks
        ("Hola. ¿Cómo estás? Muy bien.", ["Hola.", "¿Cómo estás?", "Muy bien."]),
        ("Vamos. ¡Qué bien! ¿Y tú?", ["Vamos.", "¡Qué bien!", "¿Y tú?"]),
        # Leading quotes, straight and curly
        (
            'He left. "Hello there." Then silence.',
            ["He left.", '"Hello there."', "Then silence."],
        ),
        (
            "He left. “Hello there.” Then silence.",
            ["He left.", "“Hello there.”", "Then silence."],
        ),
        (
            "He left. 'Hello there.' Then silence.",
            ["He left.", "'Hello there.'", "Then silence."],
        ),
        # German „...“ -- the closing “ is English's opening quote
        ("Er sagte. „Hallo.“ Und dann.", ["Er sagte.", "„Hallo.“", "Und dann."]),
        # French spaces its guillemets off from the text
        ("Il a dit. « Bonjour. » Fin.", ["Il a dit.", "« Bonjour. » Fin."]),
        # Stacked openers
        ("Wait. «¿Qué pasa?» Nada.", ["Wait.", "«¿Qué pasa?»", "Nada."]),
    ),
)
def test_opening_punctuation(text: str, expected_sentences: List[str]) -> None:
    """Test that a sentence may begin with punctuation before its first letter."""
    assert list(stream_to_sentences([text])) == expected_sentences


@pytest.mark.parametrize(
    ("text", "expected_sentences"),
    (
        # A citation after a quotation is not a new sentence...
        ('"A quote [...]" (Smith 55).', ['"A quote [...]" (Smith 55).']),
        # ...nor is a parenthetical aside, so brackets are not openers.
        ("The result. (See below.)", ["The result. (See below.)"]),
        ("Use it, e.g. (see docs) for more.", ["Use it, e.g. (see docs) for more."]),
        # An asterisk is not an opener either, so markdown lists stay intact.
        ("First. 2. **Item** here.", ["First.", "2. Item here."]),
        # An opener still requires a following capital.
        ('He left. "hello there."', ['He left. "hello there."']),
        # An abbreviation before a quote is still held.
        ('Mr. "Smith" arrived.', ['Mr. "Smith" arrived.']),
    ),
)
def test_opening_punctuation_non_boundaries(
    text: str, expected_sentences: List[str]
) -> None:
    """Test punctuation that looks like an opener but does not start a sentence."""
    assert list(stream_to_sentences([text])) == expected_sentences


def test_quotes() -> None:
    text_chunks = ['"First test sentence', ".", '"', " Second test sentence."]
    assert list(stream_to_sentences(text_chunks)) == [
        '"First test sentence."',
        "Second test sentence.",
    ]
