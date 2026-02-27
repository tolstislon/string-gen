"""Module tests."""

import math
import random
import re
import string
from itertools import islice
from typing import Callable, Generator, Iterator, Union

import pytest

from string_gen import (
    StringGen,
    StringGenError,
    StringGenMaxIterationsReachedError,
    StringGenPatternError,
    alphabets,
    configure,
    patterns,
    reset,
)
from string_gen.alphabets import CJK
from string_gen.generator import (
    _DEFAULT_CATEGORIES,
    _DEFAULT_MAX_REPEAT,
    OPCODES,
    _config,
    _Counter,
    _Enumerator,
    _Parser,
)

try:
    import re._parser as parse  # ty: ignore[unresolved-import]
except ImportError:  # pragma: no cover
    import sre_parse as parse

REGEX = (
    r"^\d{5}$",
    r"^#[a-fA-F0-9]{3,6}$",
    r"^#([A-F0-9]{3}|[A-F0-9]{6})$",
    r"^([0-9]{11}|(?:2131|1800|35\d{3})\d{11})$",
    r"^\s+$",
    r"^.+$",
    r"^.*$",
    r"^\W*$",
    r"^\D*$",
    r"^(?# comment)A\d$",
    r"^def (?P<name>[a-z][a-z_]{1,})\(([a-z]{1,2}: int = \d)?\)( -> int)?:$",
    r"^([A-Z][a-z]{1,15}\n){4,}[^\s]\w{1,15}\n\W{3}$",
)

NOT_SUPPORT = (r"(<)?(\w+@\w+(?:\.\w+)+)(?(1)>|$)",)


@pytest.mark.parametrize("strip", (True, False))
@pytest.mark.parametrize("regex", REGEX)
def test_regex_render(regex: str, strip: bool):
    gen = StringGen(regex.strip("^$") if strip else regex)
    value = gen.render()
    assert re.match(regex, value)


@pytest.mark.parametrize("regex", NOT_SUPPORT)
def test_opcode_error(regex: str):
    gen = StringGen(regex)
    with pytest.raises(StringGenError, match="Unsupported opcode"):
        gen.render()


def test_support_pattern():
    pattern = re.compile(r"\d")
    gen = StringGen(pattern)
    value = gen.render()
    assert gen.pattern.match(value)


def test_support_bytes():
    regex = r"\d"
    gen = StringGen(regex.encode("utf-8"))
    value = gen.render()
    assert re.match(regex, value)


def test_invalid_pattern():
    with pytest.raises(StringGenPatternError):
        StringGen(".**")


@pytest.mark.parametrize("regex", REGEX)
def test_render_list(regex: str):
    count = random.randint(1, 100)
    gen = StringGen(regex)
    values = gen.render_list(count)
    assert len(values) == count
    for value in values:
        assert re.match(regex, value)


@pytest.mark.parametrize("regex", REGEX)
def test_render_set(regex: str):
    count = random.randint(1, 5)
    gen = StringGen(regex)
    values = gen.render_set(count)
    assert len(values) == count
    for value in values:
        assert re.match(regex, value)


@pytest.mark.parametrize(
    ("regex", "expected_len"),
    (
        (r"\d{200}", 200),
        (r"\d{50,200}", None),
        (r"\w{150}", 150),
    ),
)
def test_repeat_explicit_range(regex: str, expected_len: int):
    gen = StringGen(regex)
    value = gen.render()
    if expected_len is not None:
        assert len(value) == expected_len
    else:
        assert 50 <= len(value) <= 200


@pytest.mark.parametrize(
    ("regex", "min_len", "max_len"),
    (
        (r"\w+", 1, 100),
        (r"\w*", 0, 100),
        (r"\d+", 1, 100),
        (r"\d*", 0, 100),
    ),
)
def test_repeat_unbounded(regex: str, min_len: int, max_len: int):
    gen = StringGen(regex)
    for _ in range(50):
        value = gen.render()
        assert min_len <= len(value) <= max_len


@pytest.mark.parametrize(
    ("regex", "allowed", "forbidden"),
    (
        (r"\d", set(string.digits), None),
        (r"\D", None, set(string.digits)),
        (r"\w", set(string.ascii_letters + string.digits + "_"), None),
        (r"\W", None, set(string.ascii_letters + string.digits + "_")),
        (r"\s", set(string.whitespace), None),
        (r"\S", None, set(string.whitespace)),
    ),
)
def test_categories(regex: str, allowed: set, forbidden: set):
    gen = StringGen(regex)
    count = min(30, len(allowed) if allowed else 30)
    values = gen.render_set(count=count)
    if allowed is not None:
        assert values <= allowed, f"Unexpected chars: {values - allowed}"
    if forbidden is not None:
        assert not (values & forbidden), f"Forbidden chars found: {values & forbidden}"


def test_render_set_max_iterations_error():
    gen = StringGen(r"[ab]{5}")
    with pytest.raises(StringGenMaxIterationsReachedError):
        gen.render_set(count=32, max_iteration=32)


def test_render_set_invalid_max_iteration():
    gen = StringGen(r"\d")
    with pytest.raises(ValueError, match=r"max_iteration .* must be >= count"):
        gen.render_set(count=11, max_iteration=2)


def test_set_seed():
    gen1 = StringGen(r"\d{10}", seed=b"12")
    gen2 = StringGen(r"\d{10}", seed=b"12")
    assert gen1.render_list(count=5) == gen2.render_list(count=5)


def test_set_seed_method():
    gen = StringGen(r"\d{10}")
    gen.seed(b"12")
    first_run = gen.render_list(count=5)
    gen.seed(b"12")
    second_run = gen.render_list(count=5)
    assert first_run == second_run


@pytest.mark.parametrize("regex", (r"\d", rb"\d"))
@pytest.mark.parametrize("mode", ("str", "string_gen", "pattern"))
def test_equal(mode: str, regex: Union[str, bytes]):
    new_regex = regex
    if mode == "pattern":
        new_regex = re.compile(regex)
    elif mode == "string_gen":
        new_regex = StringGen(regex)  # ty: ignore[invalid-argument-type]
    assert StringGen(regex) == new_regex  # ty: ignore[invalid-argument-type]


def test_equal_error():
    gen = StringGen(r"\d")
    with pytest.raises(TypeError):
        assert gen == 1


@pytest.mark.parametrize("regex", (r"\d", rb"\d"))
@pytest.mark.parametrize("mode", ("str", "string_gen", "pattern"))
def test_not_equal(mode: str, regex: Union[str, bytes]):
    new_regex = regex
    if mode == "pattern":
        new_regex = re.compile(regex)
    elif mode == "string_gen":
        new_regex = StringGen(regex)  # ty: ignore[invalid-argument-type]
    assert StringGen(r"\w") != new_regex


def test_bool():
    assert not StringGen("")
    assert StringGen("[1]+")


def test_or():
    gen1 = StringGen(r"^\d$")
    gen2 = StringGen(rb"^\w$")
    gen1 |= gen2
    assert re.match(r"^\d\w$", gen1.render())


def test_or_pattern():
    gen = StringGen(r"^\d$") | StringGen(r"^\w$")
    assert gen.pattern.pattern == b"^\\d\\w$"


@pytest.mark.parametrize("func", (str, repr))
def test_str_repr(func: Callable[[StringGen], str]):
    regex = r"^\d$"
    assert func(StringGen(regex)) == f"{StringGen.__name__}({regex!r})"


def test_render_list_empty():
    gen = StringGen(r"\d")
    assert gen.render_list(count=0) == []


def test_render_set_empty():
    gen = StringGen(r"\d")
    assert gen.render_set(count=0) == set()


def test_render_empty_pattern():
    gen = StringGen("")
    assert gen.render() == ""


def test_lookahead():
    gen = StringGen(r"(?=\d)\d{3}")
    value = gen.render()
    assert re.match(r"^\d{4}$", value)


def test_negative_lookahead():
    gen = StringGen(r"(?!xyz)abc")
    assert gen.render() == "abc"


def test_named_group_backref():
    gen = StringGen(r"(?P<digit>\d)_(?P=digit)")
    value = gen.render()
    assert value[0] == value[2]
    assert re.match(r"^(\d)_\1$", value)


def test_not_equal_error():
    gen = StringGen(r"\d")
    with pytest.raises(TypeError):
        assert gen != 1


def test_not_literal_opcode():
    parser = _Parser(seed=42)
    handler = OPCODES[parse.NOT_LITERAL]
    result = handler(parser, ord("a"))
    assert result != "a"
    assert result in string.printable


def test_render_list_negative_count():
    gen = StringGen(r"\d")
    with pytest.raises(ValueError, match=r"count must be >= 0"):
        gen.render_list(-1)


def test_render_set_negative_count():
    gen = StringGen(r"\d")
    with pytest.raises(ValueError, match=r"count must be >= 0"):
        gen.render_set(-1)


@pytest.mark.parametrize("seed", (42, 3.14, "hello", b"bytes", bytearray(b"ba")))
def test_seed_types(seed: Union[int, float, str, bytes, bytearray]):
    gen1 = StringGen(r"\d{10}", seed=seed)
    gen2 = StringGen(r"\d{10}", seed=seed)
    assert gen1.render_list(count=5) == gen2.render_list(count=5)


@pytest.mark.parametrize(
    ("regex", "min_len", "max_len"),
    (
        (r"\d{1,5}?", 1, 5),
        (r"\w+?", 1, 100),
        (r"\w*?", 0, 100),
        (r"\d??", 0, 1),
    ),
)
def test_lazy_quantifiers(regex: str, min_len: int, max_len: int):
    gen = StringGen(regex)
    for _ in range(50):
        value = gen.render()
        assert min_len <= len(value) <= max_len


def test_unhashable():
    gen = StringGen(r"\d")
    with pytest.raises(TypeError):
        hash(gen)


def test_seed_reproducibility_not_word():
    gen1 = StringGen(r"\W{20}", seed=42)
    gen2 = StringGen(r"\W{20}", seed=42)
    assert gen1.render() == gen2.render()


def test_seed_reproducibility_negated_class():
    gen1 = StringGen(r"[^a]{20}", seed=42)
    gen2 = StringGen(r"[^a]{20}", seed=42)
    assert gen1.render() == gen2.render()


# --- Iterator / stream tests ---


class TestIterator:
    """Tests for __iter__ / __next__ protocol."""

    def test_iter_returns_self(self):
        gen = StringGen(r"\d")
        assert iter(gen) is gen

    def test_next_returns_string(self):
        gen = StringGen(r"\d")
        value = next(gen)
        assert isinstance(value, str)
        assert re.match(r"^\d$", value)

    def test_next_matches_pattern(self):
        regex = r"[A-Z]{3}-\d{3}"
        gen = StringGen(regex)
        for _ in range(50):
            assert re.match(f"^{regex}$", next(gen))

    def test_iter_in_for_loop(self):
        gen = StringGen(r"\d{4}")
        values = []
        for value in gen:
            values.append(value)
            if len(values) == 10:
                break
        assert len(values) == 10
        for value in values:
            assert re.match(r"^\d{4}$", value)

    def test_iter_with_islice(self):
        gen = StringGen(r"\w{5}")
        values = list(islice(gen, 20))
        assert len(values) == 20
        for value in values:
            assert isinstance(value, str)
            assert len(value) == 5

    def test_iter_is_infinite(self):
        gen = StringGen(r"\d")
        count = 0
        for _ in gen:
            count += 1
            if count >= 1000:
                break
        assert count == 1000

    def test_iter_seed_reproducibility(self):
        gen1 = StringGen(r"\d{10}", seed=42)
        gen2 = StringGen(r"\d{10}", seed=42)
        values1 = list(islice(gen1, 10))
        values2 = list(islice(gen2, 10))
        assert values1 == values2

    def test_iter_empty_pattern(self):
        gen = StringGen("")
        value = next(gen)
        assert value == ""

    def test_iter_multiple_loops(self):
        gen = StringGen(r"\d", seed=42)
        first = list(islice(gen, 5))
        second = list(islice(gen, 5))
        assert len(first) == 5
        assert len(second) == 5
        assert first != second or all(v == first[0] for v in first + second)

    def test_isinstance_iterator(self):
        gen = StringGen(r"\d")
        assert isinstance(gen, Iterator)


class TestStream:
    """Tests for the stream() method."""

    def test_stream_returns_iterator(self):
        gen = StringGen(r"\d")
        result = gen.stream(5)
        assert hasattr(result, "__iter__")
        assert hasattr(result, "__next__")

    def test_stream_yields_correct_count(self):
        gen = StringGen(r"\d{3}")
        values = list(gen.stream(10))
        assert len(values) == 10

    def test_stream_values_match_pattern(self):
        regex = r"[A-Z]{2}-\d{4}"
        gen = StringGen(regex)
        for value in gen.stream(50):
            assert re.match(f"^{regex}$", value)

    def test_stream_zero_count(self):
        gen = StringGen(r"\d")
        values = list(gen.stream(0))
        assert values == []

    def test_stream_negative_count(self):
        gen = StringGen(r"\d")
        with pytest.raises(ValueError, match=r"count must be >= 0"):
            list(gen.stream(-1))

    def test_stream_is_lazy(self):
        gen = StringGen(r"\d{4}")
        stream = gen.stream(1_000_000)
        first = next(stream)
        assert isinstance(first, str)
        assert len(first) == 4

    def test_stream_seed_reproducibility(self):
        gen1 = StringGen(r"\d{10}", seed=42)
        gen2 = StringGen(r"\d{10}", seed=42)
        values1 = list(gen1.stream(10))
        values2 = list(gen2.stream(10))
        assert values1 == values2

    def test_stream_large_count(self):
        gen = StringGen(r"\d")
        count = 0
        for _ in gen.stream(5000):
            count += 1
        assert count == 5000

    def test_stream_with_complex_pattern(self):
        regex = r"(?P<digit>\d)_(?P=digit)"
        gen = StringGen(regex)
        for value in gen.stream(20):
            assert re.match(r"^(\d)_\1$", value)

    def test_stream_empty_pattern(self):
        gen = StringGen("")
        values = list(gen.stream(5))
        assert values == ["", "", "", "", ""]

    def test_stream_partial_consumption(self):
        gen = StringGen(r"\d{4}", seed=42)
        stream = gen.stream(100)
        first_three = [next(stream) for _ in range(3)]
        assert len(first_three) == 3
        for value in first_three:
            assert re.match(r"^\d{4}$", value)

    @pytest.mark.parametrize("count", (1, 5, 10, 100))
    def test_stream_parametrized_counts(self, count: int):
        gen = StringGen(r"\w{3}")
        values = list(gen.stream(count))
        assert len(values) == count


# --- max_repeat / configure tests ---


class TestMaxRepeatConstructor:
    """Tests for the max_repeat parameter in StringGen constructor."""

    def test_default_max_repeat(self):
        gen = StringGen(r"\w+")
        for _ in range(50):
            assert 1 <= len(gen.render()) <= 100

    def test_custom_max_repeat(self):
        gen = StringGen(r"\w+", max_repeat=10)
        for _ in range(50):
            assert 1 <= len(gen.render()) <= 10

    def test_max_repeat_star(self):
        gen = StringGen(r"\d*", max_repeat=5)
        for _ in range(50):
            assert len(gen.render()) <= 5

    def test_max_repeat_unbounded_range(self):
        gen = StringGen(r"\d{3,}", max_repeat=5)
        for _ in range(50):
            length = len(gen.render())
            assert 3 <= length <= 5

    def test_max_repeat_does_not_affect_bounded(self):
        gen = StringGen(r"\d{10}", max_repeat=3)
        assert len(gen.render()) == 10

    def test_max_repeat_does_not_affect_bounded_range(self):
        gen = StringGen(r"\d{5,8}", max_repeat=3)
        for _ in range(50):
            assert 5 <= len(gen.render()) <= 8

    def test_max_repeat_one(self):
        gen = StringGen(r"\d+", max_repeat=1)
        for _ in range(50):
            assert len(gen.render()) == 1

    def test_max_repeat_large(self):
        gen = StringGen(r"\d+", max_repeat=500)
        lengths = {len(gen.render()) for _ in range(100)}
        assert max(lengths) > 100

    @pytest.mark.parametrize("invalid", (0, -1, -100))
    def test_max_repeat_invalid(self, invalid: int):
        with pytest.raises(ValueError, match=r"max_repeat must be >= 1"):
            StringGen(r"\d+", max_repeat=invalid)

    def test_max_repeat_seed_reproducibility(self):
        gen1 = StringGen(r"\w+", seed=42, max_repeat=15)
        gen2 = StringGen(r"\w+", seed=42, max_repeat=15)
        assert gen1.render_list(10) == gen2.render_list(10)

    def test_max_repeat_lazy_quantifier(self):
        gen = StringGen(r"\d+?", max_repeat=8)
        for _ in range(50):
            assert 1 <= len(gen.render()) <= 8


class TestConfigure:
    """Tests for the configure() function."""

    @pytest.fixture(autouse=True)
    def _reset_config(self) -> Generator[None, None, None]:
        yield
        reset()

    def test_configure_max_repeat(self):
        configure(max_repeat=10)
        gen = StringGen(r"\w+")
        for _ in range(50):
            assert 1 <= len(gen.render()) <= 10

    def test_configure_does_not_affect_existing_instances(self):
        gen = StringGen(r"\w+")
        configure(max_repeat=5)
        for _ in range(50):
            assert 1 <= len(gen.render()) <= 100

    def test_configure_multiple_calls(self):
        configure(max_repeat=10)
        configure(max_repeat=3)
        gen = StringGen(r"\d+")
        for _ in range(50):
            assert 1 <= len(gen.render()) <= 3

    def test_configure_no_args_is_noop(self):
        configure(max_repeat=20)
        configure()
        assert _config["max_repeat"] == 20

    @pytest.mark.parametrize("invalid", (0, -1, -100))
    def test_configure_invalid_max_repeat(self, invalid: int):
        with pytest.raises(ValueError, match=r"max_repeat must be >= 1"):
            configure(max_repeat=invalid)

    def test_configure_invalid_preserves_previous(self):
        configure(max_repeat=20)
        with pytest.raises(ValueError, match=r"max_repeat must be >= 1"):
            configure(max_repeat=0)
        assert _config["max_repeat"] == 20


class TestMaxRepeatPriority:
    """Tests that constructor max_repeat > configure() > default."""

    @pytest.fixture(autouse=True)
    def _reset_config(self) -> Generator[None, None, None]:
        yield
        reset()

    def test_default_is_100(self):
        gen = StringGen(r"\w+")
        for _ in range(50):
            assert 1 <= len(gen.render()) <= 100

    def test_configure_overrides_default(self):
        configure(max_repeat=8)
        gen = StringGen(r"\d+")
        for _ in range(50):
            assert 1 <= len(gen.render()) <= 8

    def test_constructor_overrides_configure(self):
        configure(max_repeat=50)
        gen = StringGen(r"\d+", max_repeat=3)
        for _ in range(50):
            assert 1 <= len(gen.render()) <= 3

    def test_constructor_none_uses_configure(self):
        configure(max_repeat=7)
        gen = StringGen(r"\d+")
        for _ in range(50):
            assert 1 <= len(gen.render()) <= 7

    def test_reset_configure_to_default(self):
        configure(max_repeat=5)
        configure(max_repeat=_DEFAULT_MAX_REPEAT)
        gen = StringGen(r"\w+")
        for _ in range(50):
            assert 1 <= len(gen.render()) <= 100


# --- Alphabet tests ---

CYRILLIC = "абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
CYRILLIC_WORD = set(CYRILLIC + string.digits + "_")
CYRILLIC_PRINTABLE = CYRILLIC + string.digits + "_" + string.punctuation + string.whitespace


class TestAlphabetConstructor:
    """Tests for the alphabet parameter in StringGen constructor."""

    def test_default_ascii(self):
        gen = StringGen(r"\w{50}", seed=42)
        value = gen.render()
        assert all(c in string.ascii_letters + string.digits + "_" for c in value)

    def test_cyrillic_word(self):
        gen = StringGen(r"\w{50}", seed=42, alphabet=CYRILLIC)
        value = gen.render()
        assert all(c in CYRILLIC_WORD for c in value)
        assert any(c in CYRILLIC for c in value)

    def test_cyrillic_digit_unchanged(self):
        gen = StringGen(r"\d{20}", seed=42, alphabet=CYRILLIC)
        value = gen.render()
        assert all(c in string.digits for c in value)

    def test_cyrillic_space_unchanged(self):
        gen = StringGen(r"\s{20}", seed=42, alphabet=CYRILLIC)
        value = gen.render()
        assert all(c in string.whitespace for c in value)

    def test_cyrillic_dot(self):
        gen = StringGen(r".{100}", seed=42, alphabet=CYRILLIC)
        value = gen.render()
        assert all(c in CYRILLIC_PRINTABLE.replace("\n", "") for c in value)

    def test_cyrillic_negated_class(self):
        gen = StringGen(r"[^а]{50}", seed=42, alphabet=CYRILLIC)  # noqa: RUF001
        value = gen.render()
        assert "а" not in value  # noqa: RUF001
        assert all(c in CYRILLIC_PRINTABLE for c in value)

    def test_cyrillic_not_literal(self):
        parser = _Parser(seed=42, alphabet=CYRILLIC)
        handler = OPCODES[parse.NOT_LITERAL]
        result = handler(parser, ord("а"))  # noqa: RUF001
        assert result != "а"  # noqa: RUF001
        assert result in CYRILLIC_PRINTABLE

    def test_custom_small_alphabet(self):
        gen = StringGen(r"\w{50}", seed=42, alphabet="abc")
        value = gen.render()
        assert all(c in set("abc" + string.digits + "_") for c in value)

    def test_alphabet_composition(self):
        mixed = CYRILLIC + string.ascii_letters
        gen = StringGen(r"\w{100}", seed=42, alphabet=mixed)
        value = gen.render()
        assert all(c in set(mixed + string.digits + "_") for c in value)

    def test_alphabet_with_explicit_range(self):
        gen = StringGen(r"[а-я]{20}", seed=42, alphabet=string.ascii_letters)  # noqa: RUF001
        value = gen.render()
        assert all("а" <= c <= "я" for c in value)  # noqa: RUF001

    def test_seed_reproducibility_with_alphabet(self):
        gen1 = StringGen(r"\w{20}", seed=42, alphabet=CYRILLIC)
        gen2 = StringGen(r"\w{20}", seed=42, alphabet=CYRILLIC)
        assert gen1.render() == gen2.render()

    def test_alphabet_with_max_repeat(self):
        gen = StringGen(r"\w+", seed=42, alphabet=CYRILLIC, max_repeat=10)
        for _ in range(50):
            value = gen.render()
            assert 1 <= len(value) <= 10
            assert all(c in CYRILLIC_WORD for c in value)


class TestAlphabetConfigure:
    """Tests for alphabet in configure()."""

    @pytest.fixture(autouse=True)
    def _reset_config(self) -> Generator[None, None, None]:
        yield
        reset()

    def test_configure_alphabet(self):
        configure(alphabet=CYRILLIC)
        gen = StringGen(r"\w{50}", seed=42)
        value = gen.render()
        assert all(c in CYRILLIC_WORD for c in value)
        assert any(c in CYRILLIC for c in value)

    def test_configure_does_not_affect_existing(self):
        gen = StringGen(r"\w{50}", seed=42)
        configure(alphabet=CYRILLIC)
        value = gen.render()
        assert all(c in string.ascii_letters + string.digits + "_" for c in value)

    def test_constructor_overrides_configure(self):
        configure(alphabet="xyz")
        gen = StringGen(r"\w{50}", seed=42, alphabet=CYRILLIC)
        value = gen.render()
        assert all(c in CYRILLIC_WORD for c in value)

    def test_configure_invalid_alphabet_empty(self):
        with pytest.raises(TypeError, match=r"alphabet must be a non-empty string"):
            configure(alphabet="")

    def test_configure_invalid_alphabet_type(self):
        with pytest.raises(TypeError, match=r"alphabet must be a non-empty string"):
            configure(alphabet=123)  # ty: ignore[invalid-argument-type]


class TestReset:
    """Tests for the reset() function."""

    @pytest.fixture(autouse=True)
    def _reset_config(self) -> Generator[None, None, None]:
        yield
        reset()

    def test_reset_restores_defaults(self):
        configure(max_repeat=10, alphabet=CYRILLIC)
        reset()
        assert _config["max_repeat"] == _DEFAULT_MAX_REPEAT
        assert _config["alphabet"] is None

    def test_reset_does_not_affect_existing_instances(self):
        gen = StringGen(r"\w{20}", seed=42, alphabet=CYRILLIC)
        reset()
        value = gen.render()
        assert all(c in CYRILLIC_WORD for c in value)

    def test_reset_new_instances_use_defaults(self):
        configure(max_repeat=5, alphabet=CYRILLIC)
        reset()
        gen = StringGen(r"\w{20}", seed=42)
        value = gen.render()
        assert all(c in string.ascii_letters + string.digits + "_" for c in value)


class TestAlphabetPresets:
    """Tests for all presets from alphabets module."""

    @pytest.fixture(autouse=True)
    def _reset_config(self) -> Generator[None, None, None]:
        yield
        reset()

    @pytest.mark.parametrize(
        "preset_name",
        (
            "ASCII",
            "CYRILLIC",
            "GREEK",
            "LATIN_EXTENDED",
            "HIRAGANA",
            "KATAKANA",
            "HANGUL",
            "ARABIC",
            "DEVANAGARI",
            "THAI",
            "HEBREW",
            "BENGALI",
            "TAMIL",
            "TELUGU",
            "GEORGIAN",
            "ARMENIAN",
            "ETHIOPIC",
            "MYANMAR",
            "SINHALA",
            "GUJARATI",
            "PUNJABI",
        ),
    )
    def test_preset_word_generation(self, preset_name: str):
        alphabet = getattr(alphabets, preset_name)
        allowed = set(alphabet + string.digits + "_")
        gen = StringGen(r"\w{20}", seed=42, alphabet=alphabet)
        value = gen.render()
        assert len(value) == 20
        assert all(c in allowed for c in value)

    def test_cjk_preset(self):
        allowed = set(CJK + string.digits + "_")
        gen = StringGen(r"\w{5}", seed=42, alphabet=CJK)
        value = gen.render()
        assert len(value) == 5
        assert all(c in allowed for c in value)


# --- Built-in pattern tests ---

ALL_PATTERNS = (
    "UUID4",
    "OBJECT_ID",
    "IPV4",
    "IPV6_SHORT",
    "MAC_ADDRESS",
    "HEX_COLOR",
    "HEX_COLOR_SHORT",
    "SLUG",
    "SEMVER",
    "DATE_ISO",
    "TIME_24H",
    "JWT_LIKE",
    "API_KEY",
)


class TestPatterns:
    """Tests for built-in patterns from patterns module."""

    @pytest.mark.parametrize("pattern_name", ALL_PATTERNS)
    def test_pattern_matches_fullmatch(self, pattern_name: str):
        pattern = getattr(patterns, pattern_name)
        gen = StringGen(pattern, seed=42)
        for _ in range(20):
            value = gen.render()
            assert re.fullmatch(pattern, value), f"{pattern_name}: {value!r} does not match {pattern!r}"

    @pytest.mark.parametrize("pattern_name", ALL_PATTERNS)
    def test_pattern_seed_reproducibility(self, pattern_name: str):
        pattern = getattr(patterns, pattern_name)
        gen1 = StringGen(pattern, seed=42)
        gen2 = StringGen(pattern, seed=42)
        assert gen1.render_list(10) == gen2.render_list(10)

    def test_uuid4_format(self):
        gen = StringGen(patterns.UUID4, seed=42)
        for _ in range(50):
            value = gen.render()
            parts = value.split("-")
            assert len(parts) == 5
            assert len(parts[0]) == 8
            assert len(parts[1]) == 4
            assert len(parts[2]) == 4
            assert len(parts[3]) == 4
            assert len(parts[4]) == 12
            assert parts[2][0] == "4"
            assert parts[3][0] in "89ab"

    def test_ipv4_valid_octets(self):
        gen = StringGen(patterns.IPV4, seed=42)
        for _ in range(50):
            value = gen.render()
            octets = value.split(".")
            assert len(octets) == 4
            for octet in octets:
                assert 0 <= int(octet) <= 255

    def test_semver_no_leading_zeros(self):
        gen = StringGen(patterns.SEMVER, seed=42)
        for _ in range(100):
            value = gen.render()
            parts = value.split(".")
            assert len(parts) == 3
            for part in parts:
                if len(part) > 1:
                    assert part[0] != "0", f"Leading zero in semver: {value!r}"

    def test_date_iso_valid_ranges(self):
        gen = StringGen(patterns.DATE_ISO, seed=42)
        for _ in range(100):
            value = gen.render()
            parts = value.split("-")
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            assert 2020 <= year <= 2039
            assert 1 <= month <= 12
            assert 1 <= day <= 31

    def test_time_24h_valid_ranges(self):
        gen = StringGen(patterns.TIME_24H, seed=42)
        for _ in range(100):
            value = gen.render()
            parts = value.split(":")
            hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
            assert 0 <= hours <= 23
            assert 0 <= minutes <= 59
            assert 0 <= seconds <= 59


class TestPatternsAlphabetSafe:
    """Tests that patterns produce correct results regardless of custom alphabet."""

    @pytest.mark.parametrize("pattern_name", ALL_PATTERNS)
    def test_pattern_with_cyrillic_alphabet(self, pattern_name: str):
        pattern = getattr(patterns, pattern_name)
        gen = StringGen(pattern, seed=42, alphabet=CYRILLIC)
        for _ in range(20):
            value = gen.render()
            assert re.fullmatch(pattern, value), f"{pattern_name} with CYRILLIC: {value!r} does not match {pattern!r}"


# --- count() tests ---


class TestCount:
    """Tests for the count() method."""

    @pytest.mark.parametrize(
        ("regex", "expected"),
        (
            (r"a", 1),
            (r"[a-z]", 26),
            (r"\d", 10),
            (r"[01]{3}", 8),
            (r"(a|b|c)", 3),
            (r"[ab]{2,3}", 12),
            (r"a?", 2),
            (r"(\d)\1", 10),
            (r"", 1),
            (r"a{0,2}", 3),
        ),
    )
    def test_finite_count(self, regex: str, expected: int):
        assert StringGen(regex).count() == expected

    @pytest.mark.parametrize("regex", (r"\d+", r"\d*", r"\w{3,}"))
    def test_infinite_count(self, regex: str):
        assert StringGen(regex).count() == math.inf

    def test_count_cached(self):
        gen = StringGen(r"[a-z]")
        first = gen.count()
        second = gen.count()
        assert first == second == 26

    def test_count_custom_alphabet(self):
        gen = StringGen(r"\w", alphabet="abc")
        expected = len(set("abc" + string.digits + "_"))
        assert gen.count() == expected

    def test_count_not_literal(self):
        gen = StringGen(r"[^a]", alphabet="abc")
        printable = set("abc" + string.digits + "_" + string.punctuation + string.whitespace)
        assert gen.count() == len(printable - {"a"})

    def test_count_negated_class(self):
        gen = StringGen(r"[^ab]", alphabet="abc")
        printable = set("abc" + string.digits + "_" + string.punctuation + string.whitespace)
        assert gen.count() == len(printable - {"a", "b"})

    def test_count_any(self):
        gen = StringGen(r".", alphabet="ab")
        printable = set("ab" + string.digits + "_" + string.punctuation + string.whitespace)
        assert gen.count() == len(printable - {"\n"})

    def test_count_assert(self):
        gen = StringGen(r"(?=\d)\d")
        assert gen.count() == 100  # 10 * 10

    def test_count_assert_not(self):
        gen = StringGen(r"(?!x)\d")
        assert gen.count() == 10  # 1 * 10

    def test_count_not_literal_single(self):
        gen = StringGen(r"[^\n]", alphabet="ab")
        printable = set("ab" + string.digits + "_" + string.punctuation + string.whitespace)
        assert gen.count() == len(printable - {"\n"})

    def test_count_unsupported_opcode(self):
        counter = _Counter(_DEFAULT_CATEGORIES, string.printable)
        with pytest.raises(StringGenError, match="Unsupported opcode"):
            counter._node((999, None))  # noqa: SLF001

    def test_count_repeat_inner_zero(self):
        counter = _Counter(_DEFAULT_CATEGORIES, string.printable)
        inner_pattern = [(parse.IN, [])]
        result = counter._count_repeat((1, 3, inner_pattern))  # noqa: SLF001
        assert result == 0

    def test_count_repeat_inner_infinite_bounded(self):
        counter = _Counter(_DEFAULT_CATEGORIES, string.printable)
        inner_pattern = [(parse.MAX_REPEAT, (1, parse.MAXREPEAT, [(parse.LITERAL, 97)]))]
        result = counter._count_repeat((1, 3, inner_pattern))  # noqa: SLF001
        assert result == math.inf


# --- enumerate() tests ---


class TestEnumerate:
    """Tests for the enumerate() method."""

    def test_literal(self):
        assert list(StringGen(r"abc").enumerate()) == ["abc"]

    def test_char_class(self):
        assert list(StringGen(r"[abc]").enumerate()) == ["a", "b", "c"]

    def test_digit(self):
        assert list(StringGen(r"\d").enumerate()) == [str(i) for i in range(10)]

    def test_branch(self):
        assert list(StringGen(r"yes|no").enumerate()) == ["yes", "no"]

    def test_repeat_fixed(self):
        assert list(StringGen(r"[ab]{2}").enumerate()) == ["aa", "ab", "ba", "bb"]

    def test_optional(self):
        assert list(StringGen(r"a?").enumerate()) == ["", "a"]

    def test_groupref(self):
        assert list(StringGen(r"([ab])\1").enumerate()) == ["aa", "bb"]

    def test_empty_pattern(self):
        assert list(StringGen(r"").enumerate()) == [""]

    def test_sequence(self):
        assert list(StringGen(r"[ab][12]").enumerate()) == ["a1", "a2", "b1", "b2"]

    def test_repeat_range(self):
        assert list(StringGen(r"a{1,3}").enumerate()) == ["a", "aa", "aaa"]

    def test_limit_unbounded(self):
        result = list(StringGen(r"\d+").enumerate(limit=1))
        assert len(result) == 10

    def test_limit_invalid(self):
        with pytest.raises(ValueError, match=r"limit must be >= 1"):
            list(StringGen(r"\d+").enumerate(limit=0))

    def test_lazy_iterator(self):
        it = StringGen(r"[abc]").enumerate()
        assert hasattr(it, "__next__")

    def test_deterministic(self):
        gen = StringGen(r"[ab]{2}")
        assert list(gen.enumerate()) == list(gen.enumerate())

    def test_enumerate_not_literal(self):
        gen = StringGen(r"[^a]", alphabet="ab")
        result = list(gen.enumerate())
        assert "a" not in result
        assert len(result) > 0

    def test_enumerate_any(self):
        gen = StringGen(r".", alphabet="ab")
        result = list(gen.enumerate())
        assert "\n" not in result
        assert len(result) > 0

    def test_enumerate_anchor(self):
        result = list(StringGen(r"^a$").enumerate())
        assert result == ["a"]

    def test_enumerate_assert(self):
        result = list(StringGen(r"(?=[ab])[ab]").enumerate())
        assert sorted(result) == ["aa", "ab", "ba", "bb"]

    def test_enumerate_assert_not(self):
        result = list(StringGen(r"(?!x)[ab]").enumerate())
        assert result == ["a", "b"]

    def test_enumerate_unsupported_opcode(self):
        enumerator = _Enumerator(_DEFAULT_CATEGORIES, string.printable, 100)
        with pytest.raises(StringGenError, match="Unsupported opcode"):
            list(enumerator._node((999, None), {}))  # noqa: SLF001

    def test_enumerate_negated_class(self):
        gen = StringGen(r"[^ab]", alphabet="abc")
        result = list(gen.enumerate())
        assert "a" not in result
        assert "b" not in result
        assert len(result) > 0

    def test_count_matches_enumerate(self):
        for regex in (r"[abc]", r"[01]{3}", r"(yes|no)", r"a{0,2}", r"([ab])\1"):
            gen = StringGen(regex)
            assert len(list(gen.enumerate())) == gen.count(), f"Mismatch for {regex!r}"


# --- render_set early error tests ---


class TestRenderSetEarlyError:
    """Tests for the early ValueError in render_set when count exceeds available."""

    def test_render_set_exceeds_available(self):
        with pytest.raises(ValueError, match=r"Cannot generate 3 unique strings"):
            StringGen(r"[01]").render_set(3)

    def test_render_set_exact_available(self):
        result = StringGen(r"[01]").render_set(2)
        assert result == {"0", "1"}
