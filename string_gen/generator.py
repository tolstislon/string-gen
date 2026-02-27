"""
Random string generation from regular expression patterns.

Provides the :class:`StringGen` class which compiles a regex pattern and
produces random strings matching that pattern. Useful for generating test
data, fixtures, fuzzing inputs, and mock data.
"""

import math
import random
import re
import string
from itertools import chain
from typing import Any, AnyStr, Callable, Dict, Final, Iterator, List, Sequence, Set, Tuple, Union

try:
    import re._parser as parse  # ty: ignore[unresolved-import]
except ImportError:  # pragma: no cover
    import sre_parse as parse

SeedType = Union[int, float, str, bytes, bytearray, None]


class StringGenError(Exception):
    """Base exception for all string-gen errors."""


class StringGenPatternError(StringGenError):
    """
    Exception raised when an invalid regex pattern is provided.

    :param pattern: The pattern that failed to compile.
    """

    def __init__(self, pattern: Union[re.Pattern, AnyStr], *args) -> None:  # noqa: ANN002
        super().__init__(f"Invalid pattern: {pattern!r}", *args)


class StringGenMaxIterationsReachedError(StringGenError):
    """
    Exception raised when ``render_set`` exhausts its iteration budget.

    :param max_iterations: The iteration limit that was reached.
    """

    def __init__(self, max_iterations: int, *args) -> None:  # noqa: ANN002
        super().__init__(f"Max iterations reached: {max_iterations!r}", *args)


def _build_categories(alphabet: str, printable: str) -> Dict[int, str]:
    """
    Build a category lookup table for the given alphabet.

    :param alphabet: Letters to use in place of ``string.ascii_letters``.
    :param printable: Full printable character set derived from *alphabet*.
    """
    word = alphabet + string.digits + "_"
    return {
        parse.CATEGORY_DIGIT: string.digits,
        parse.CATEGORY_NOT_DIGIT: "".join(c for c in printable if c not in string.digits),
        parse.CATEGORY_SPACE: string.whitespace,
        parse.CATEGORY_NOT_SPACE: "".join(c for c in printable if c not in string.whitespace),
        parse.CATEGORY_WORD: word,
        parse.CATEGORY_NOT_WORD: "".join(c for c in printable if c not in word),
    }


# Default category table built from ASCII letters.
_DEFAULT_CATEGORIES: Final[Dict[int, str]] = _build_categories(string.ascii_letters, string.printable)


def _chars_in_class(items: List[Tuple[int, Any]], categories: Dict[int, str], printable: str) -> List[str]:
    """
    Collect all characters matched by a character class (``[...]``).

    :param items: Parsed items inside the character class.
    :param categories: Category lookup table.
    :param printable: Full printable character set.
    """
    negate = False
    chars: List[str] = []
    for op, value in items:
        if op == parse.NEGATE:
            negate = True
        elif op == parse.LITERAL:
            chars.append(chr(value))
        elif op == parse.RANGE:
            chars.extend(chr(i) for i in range(value[0], value[1] + 1))
        elif op == parse.CATEGORY:
            chars.extend(categories[value])
    if negate:
        return sorted(set(printable) - set(chars))
    return sorted(set(chars))


_DEFAULT_MAX_REPEAT: Final[int] = 100

_config: Dict[str, Any] = {"max_repeat": _DEFAULT_MAX_REPEAT, "alphabet": None}


def configure(*, max_repeat: Union[int, None] = None, alphabet: Union[str, None] = None) -> None:
    """
    Configure global defaults for new ``StringGen`` instances.

    Settings apply to all subsequently created instances unless
    overridden in the constructor.  Omit a parameter to leave it unchanged.

    :param max_repeat: Maximum repetitions for unbounded quantifiers
        (``*``, ``+``, ``{n,}``).  Must be >= 1.  Default is 100.
    :param alphabet: Custom alphabet string replacing ``string.ascii_letters``
        in all character categories.  Must be a non-empty string.
    :raises ValueError: If *max_repeat* is less than 1.
    :raises TypeError: If *alphabet* is not a non-empty string.
    """
    if max_repeat is not None:
        if max_repeat < 1:
            raise ValueError(f"max_repeat must be >= 1, got {max_repeat}")
        _config["max_repeat"] = max_repeat
    if alphabet is not None:
        if not isinstance(alphabet, str) or not alphabet:
            raise TypeError(f"alphabet must be a non-empty string, got {alphabet!r}")
        _config["alphabet"] = alphabet


def reset() -> None:
    """Reset all global settings to their defaults."""
    _config["max_repeat"] = _DEFAULT_MAX_REPEAT
    _config["alphabet"] = None


def _get_bytes(val: AnyStr) -> bytes:
    """
    Convert a string or bytes value to bytes.

    :param val: A string or bytes object to convert.
    """
    if not isinstance(val, bytes):
        return val.encode("utf-8", errors="ignore")
    return val


class _Parser:
    """Internal regex AST walker that produces random strings."""

    __slots__ = ("cache", "categories", "max_repeat", "printable", "rand")

    def __init__(
        self,
        seed: SeedType = None,
        *,
        max_repeat: int = _DEFAULT_MAX_REPEAT,
        alphabet: Union[str, None] = None,
    ) -> None:
        self.cache: Dict[str, Any] = {}
        self.rand = random.Random(seed)
        self.max_repeat = max_repeat
        if alphabet is None:
            self.categories = _DEFAULT_CATEGORIES
            self.printable = string.printable
        else:
            word = alphabet + string.digits + "_"
            self.printable = word + string.punctuation + string.whitespace
            self.categories = _build_categories(alphabet, self.printable)

    def repeat(self, start_range: int, end_range: int, value: List[Any]) -> str:
        """
        Generate a repeated sequence of characters.

        Unbounded quantifiers (``*``, ``+``, ``{n,}``) are capped at
        :attr:`max_repeat`.

        :param start_range: Minimum number of repetitions.
        :param end_range: Maximum number of repetitions (``MAXREPEAT`` means unbounded).
        :param value: Parsed sub-pattern to repeat.
        """
        upper = end_range if end_range < parse.MAXREPEAT else max(start_range, self.max_repeat)
        times = self.rand.randint(start_range, upper)
        return "".join("".join(self.state(i) for i in value) for _ in range(times))

    def group(self, value: Sequence[Any]) -> str:
        """
        Generate a capturing group and cache its result.

        :param value: Tuple of ``(group_index, ..., sub_pattern)``.
        """
        result = "".join(self.state(i) for i in value[-1])
        if value[0]:
            self.cache[value[0]] = result
        return result

    def in_state(self, value: List[Any]) -> Any:
        """
        Pick a random character from a character class (``[...]``).

        :param value: List of parsed alternatives inside the class.
        """
        candidates = list(chain(*(self.state(i) for i in value)))
        if candidates[0] is False:
            candidates = sorted(set(self.printable).difference(candidates[1:]))
        return self.rand.choice(candidates)

    def state(self, state: Tuple[int, Any]) -> Any:
        """
        Dispatch a single parsed opcode to its handler.

        :param state: A ``(opcode, value)`` tuple from the parsed regex AST.
        """
        opcode, value = state
        try:
            return OPCODES[opcode](self, value)
        except KeyError:
            raise StringGenError(f"Unsupported opcode: {opcode!r}") from None

    def value(self, pattern: re.Pattern) -> str:
        """
        Parse and walk a compiled regex pattern, returning a random matching string.

        :param pattern: A compiled ``re.Pattern`` object.
        """
        parsed = parse.parse(pattern.pattern)
        result = "".join(self.state(state) for state in parsed)  # ty: ignore[invalid-argument-type]
        self.cache.clear()
        return result


# Dispatch table mapping sre_parse opcodes to handler functions.
OpcodesDict = Dict[int, Callable[[_Parser, Any], Any]]

OPCODES: Final[OpcodesDict] = {
    parse.LITERAL: lambda _, x: chr(x),
    parse.NOT_LITERAL: lambda p, x: p.rand.choice(p.printable.replace(chr(x), "")),
    parse.AT: lambda *_: "",
    parse.IN: lambda p, x: p.in_state(x),
    parse.ANY: lambda p, _: p.rand.choice(p.printable.replace("\n", "")),
    parse.RANGE: lambda _, x: [chr(i) for i in range(x[0], x[1] + 1)],
    parse.CATEGORY: lambda p, x: p.categories[x],
    parse.BRANCH: lambda p, x: "".join(p.state(i) for i in p.rand.choice(x[1])),
    parse.SUBPATTERN: lambda p, x: p.group(x),
    parse.ASSERT: lambda p, x: "".join(p.state(i) for i in x[1]),
    parse.ASSERT_NOT: lambda *_: "",
    parse.GROUPREF: lambda p, x: p.cache[x],
    parse.MIN_REPEAT: lambda p, x: p.repeat(*x),
    parse.MAX_REPEAT: lambda p, x: p.repeat(*x),
    parse.NEGATE: lambda *_: [False],
}


class _Counter:
    """Count the number of unique strings a parsed regex can produce."""

    __slots__ = ("categories", "printable")

    def __init__(self, categories: Dict[int, str], printable: str) -> None:
        self.categories = categories
        self.printable = printable

    def count(self, parsed: Sequence[Tuple[int, Any]]) -> Union[int, float]:
        """
        Return the total number of unique strings for a parsed sequence.

        :param parsed: Sequence of ``(opcode, value)`` tuples from the regex AST.
        """
        result: Union[int, float] = 1
        for node in parsed:
            result *= self._node(node)
            if result == math.inf:
                return math.inf
        return result

    def _node(self, state: Tuple[int, Any]) -> Union[int, float]:  # noqa: PLR0911
        opcode, value = state
        if opcode == parse.LITERAL:
            return 1
        if opcode == parse.NOT_LITERAL:
            return len(set(self.printable) - {chr(value)})
        if opcode == parse.AT:
            return 1
        if opcode == parse.IN:
            return len(_chars_in_class(value, self.categories, self.printable))
        if opcode == parse.ANY:
            return len(set(self.printable) - {"\n"})
        if opcode == parse.BRANCH:
            return sum(self.count(branch) for branch in value[1])
        if opcode == parse.SUBPATTERN:
            return self.count(value[-1])
        if opcode == parse.ASSERT:
            return self.count(value[1])
        if opcode == parse.ASSERT_NOT:
            return 1
        if opcode == parse.GROUPREF:
            return 1
        if opcode in (parse.MAX_REPEAT, parse.MIN_REPEAT):
            return self._count_repeat(value)
        raise StringGenError(f"Unsupported opcode: {opcode!r}")

    def _count_repeat(self, value: Tuple[int, int, List[Any]]) -> Union[int, float]:
        start, end, pattern = value
        if end >= parse.MAXREPEAT:
            return math.inf
        inner = self.count(pattern)
        if inner == 0:
            return 0
        if inner == math.inf:
            return math.inf if start > 0 or end > 0 else 1
        total: Union[int, float] = 0
        for k in range(start, end + 1):
            total += inner**k
        return total


class _Enumerator:
    """Enumerate all unique strings a parsed regex can produce."""

    __slots__ = ("categories", "max_repeat", "printable")

    def __init__(self, categories: Dict[int, str], printable: str, max_repeat: int) -> None:
        self.categories = categories
        self.printable = printable
        self.max_repeat = max_repeat

    def enumerate(self, parsed: Sequence[Tuple[int, Any]]) -> Iterator[str]:
        """
        Yield all unique strings for a parsed sequence.

        :param parsed: Sequence of ``(opcode, value)`` tuples from the regex AST.
        """
        for s, _ in self._sequence(list(parsed), {}):
            yield s

    def _sequence(self, nodes: List[Tuple[int, Any]], bindings: Dict[int, str]) -> Iterator[Tuple[str, Dict[int, str]]]:
        if not nodes:
            yield "", bindings
            return
        first, *rest = nodes
        for prefix, b in self._node(first, bindings):
            for suffix, b2 in self._sequence(rest, b):
                yield prefix + suffix, b2

    def _node(  # noqa: PLR0912
        self, state: Tuple[int, Any], bindings: Dict[int, str]
    ) -> Iterator[Tuple[str, Dict[int, str]]]:
        opcode, value = state
        if opcode == parse.LITERAL:
            yield chr(value), bindings
        elif opcode == parse.NOT_LITERAL:
            for c in self.printable:
                if c != chr(value):
                    yield c, bindings
        elif opcode == parse.AT:
            yield "", bindings
        elif opcode == parse.IN:
            for c in _chars_in_class(value, self.categories, self.printable):
                yield c, bindings
        elif opcode == parse.ANY:
            for c in self.printable:
                if c != "\n":
                    yield c, bindings
        elif opcode == parse.BRANCH:
            for branch in value[1]:
                yield from self._sequence(list(branch), bindings)
        elif opcode == parse.SUBPATTERN:
            group_id = value[0]
            for s, updated in self._sequence(list(value[-1]), bindings):
                yield s, ({**updated, group_id: s} if group_id else updated)
        elif opcode == parse.ASSERT:
            yield from self._sequence(list(value[1]), bindings)
        elif opcode == parse.ASSERT_NOT:
            yield "", bindings
        elif opcode == parse.GROUPREF:
            yield bindings.get(value, ""), bindings
        elif opcode in (parse.MAX_REPEAT, parse.MIN_REPEAT):
            yield from self._repeat(value, bindings)
        else:
            raise StringGenError(f"Unsupported opcode: {opcode!r}")

    def _repeat(
        self, value: Tuple[int, int, List[Any]], bindings: Dict[int, str]
    ) -> Iterator[Tuple[str, Dict[int, str]]]:
        start, end, pattern = value
        upper = end if end < parse.MAXREPEAT else max(start, self.max_repeat)
        for k in range(start, upper + 1):
            yield from self._repeat_n(list(pattern), k, bindings)

    def _repeat_n(
        self, pattern: List[Tuple[int, Any]], n: int, bindings: Dict[int, str]
    ) -> Iterator[Tuple[str, Dict[int, str]]]:
        if n == 0:
            yield "", bindings
            return
        for prefix, b in self._sequence(pattern, bindings):
            for suffix, b2 in self._repeat_n(pattern, n - 1, b):
                yield prefix + suffix, b2


class StringGen:
    """
    Random string generator driven by a regular expression pattern.

    Compiles the given regex and produces random strings that match it.
    Supports literals, character classes, quantifiers, groups, alternation,
    anchors, lookahead assertions, and backreferences.

    The ``max_repeat`` parameter controls the upper bound for unbounded
    quantifiers (``*``, ``+``, ``{n,}``).  It can be set per-instance
    via the constructor or globally via :func:`configure`.

    Instances are iterable: iterating yields an infinite stream of random
    matching strings. Use :meth:`stream` for a bounded lazy generator.

    Instances can be combined with ``|`` to concatenate patterns, compared
    with ``==`` against other patterns, and tested for emptiness with ``bool()``.
    """

    __slots__ = ("_cached_count", "_parser", "_pattern")
    __hash__ = None

    def __init__(
        self,
        pattern: Union[re.Pattern, AnyStr],
        seed: SeedType = None,
        *,
        max_repeat: Union[int, None] = None,
        alphabet: Union[str, None] = None,
    ) -> None:
        try:
            self._pattern: re.Pattern = re.compile(pattern)
        except re.error as error:
            raise StringGenPatternError(pattern) from error
        if max_repeat is not None and max_repeat < 1:
            raise ValueError(f"max_repeat must be >= 1, got {max_repeat}")
        effective = max_repeat if max_repeat is not None else _config["max_repeat"]
        effective_alphabet = alphabet if alphabet is not None else _config["alphabet"]
        self._parser = _Parser(seed, max_repeat=effective, alphabet=effective_alphabet)
        self._cached_count: Union[int, float, None] = None

    @property
    def pattern(self) -> re.Pattern:
        """Compiled ``re.Pattern`` object used for generation."""
        return self._pattern

    def __get_value(self, value: Any) -> re.Pattern:
        if isinstance(value, type(self)):
            return value._pattern  # noqa: SLF001
        if isinstance(value, re.Pattern):
            return value
        if isinstance(value, (str, bytes)):
            return re.compile(value)
        raise TypeError(f"Unexpected type {type(value)!r} The only supported: str, StringGen, re.Pattern")

    def __eq__(self, other: Union[re.Pattern, "StringGen", AnyStr]) -> bool:
        return self._pattern == self.__get_value(other)

    def __bool__(self) -> bool:
        return bool(self._pattern.pattern)

    def __or__(self, other: "StringGen") -> "StringGen":
        base = _get_bytes(self._pattern.pattern)
        other_bytes = _get_bytes(self.__get_value(other).pattern)
        return StringGen(base.rstrip(b"$") + other_bytes.lstrip(b"^"))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._pattern.pattern!r})"

    def __iter__(self) -> Iterator[str]:
        r"""
        Return an infinite iterator that yields random matching strings.

        Each call to ``next()`` produces a new random string via :meth:`render`.

        .. code-block:: python

            gen = StringGen(r"\d{4}")
            for value in gen:
                print(value)
                break  # without break, iterates forever
        """
        return self

    def __next__(self) -> str:
        """Produce the next random string matching the pattern."""
        return self.render()

    def seed(self, seed: SeedType = None) -> None:
        """
        Re-seed the internal random number generator.

        Calling with the same seed produces the same sequence of rendered strings.

        :param seed: Seed value accepted by ``random.Random.seed``.
        """
        self._parser.rand.seed(seed)

    def render(self) -> str:
        """Produce a single random string matching the pattern."""
        return self._parser.value(self._pattern)

    def count(self) -> Union[int, float]:
        """
        Return the number of unique strings the pattern can produce.

        Returns ``math.inf`` for patterns with unbounded quantifiers
        (``*``, ``+``, ``{n,}``).  The result is cached after the first call.
        """
        if self._cached_count is None:
            counter = _Counter(self._parser.categories, self._parser.printable)
            self._cached_count = counter.count(parse.parse(self._pattern.pattern))  # ty: ignore[invalid-argument-type]
        return self._cached_count

    def enumerate(self, *, limit: Union[int, None] = None) -> Iterator[str]:
        """
        Yield all unique strings the pattern can produce.

        For patterns with unbounded quantifiers, *limit* caps the maximum
        repetition count.  When *limit* is ``None`` the parser's
        ``max_repeat`` value is used.

        :param limit: Maximum repetitions for unbounded quantifiers.
        :raises ValueError: If *limit* is less than 1.
        """
        if limit is not None and limit < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")
        effective_limit = limit if limit is not None else self._parser.max_repeat
        enumerator = _Enumerator(self._parser.categories, self._parser.printable, effective_limit)
        yield from enumerator.enumerate(parse.parse(self._pattern.pattern))  # ty: ignore[invalid-argument-type]

    def stream(self, count: int) -> Iterator[str]:
        r"""
        Return a lazy iterator that yields *count* random matching strings.

        Unlike :meth:`render_list`, strings are generated one at a time and
        never collected into a list, making ``stream`` memory-efficient for
        large batches.

        :param count: Number of strings to yield.
        :raises ValueError: If *count* is negative.

        .. code-block:: python

            gen = StringGen(r"\d{4}")
            for value in gen.stream(1000):
                process(value)
        """
        if count < 0:
            raise ValueError(f"count must be >= 0, got {count}")
        for _ in range(count):
            yield self.render()

    def render_list(self, count: int) -> List[str]:
        """
        Produce a list of random strings matching the pattern.

        :param count: Number of strings to generate.
        """
        if count < 0:
            raise ValueError(f"count must be >= 0, got {count}")
        return [self.render() for _ in range(count)]

    def render_set(self, count: int, *, max_iteration: int = 100_000) -> Set[str]:
        """
        Produce a set of unique random strings matching the pattern.

        Keeps generating until *count* unique strings are collected or
        *max_iteration* attempts are exhausted.

        :param count: Required number of unique strings.
        :param max_iteration: Maximum generation attempts before giving up.
        :raises ValueError: If *max_iteration* is less than *count*.
        :raises StringGenMaxIterationsReachedError: If the iteration limit is reached
            before collecting enough unique strings.
        """
        if count < 0:
            raise ValueError(f"count must be >= 0, got {count}")
        if max_iteration < count:
            raise ValueError(f"max_iteration ({max_iteration}) must be >= count ({count})")
        available = self.count()
        if available != math.inf and count > available:
            raise ValueError(f"Cannot generate {count} unique strings: pattern can only produce {available}")
        values = set()
        iterations = 0
        while len(values) < count and iterations < max_iteration:
            values.add(self.render())
            iterations += 1
        if iterations >= max_iteration and len(values) != count:
            raise StringGenMaxIterationsReachedError(max_iteration)
        return values
