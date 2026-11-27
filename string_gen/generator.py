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
from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from typing import Any, Final, TypeVar

from ._backrefs import Atom, count_union

try:
    import re._parser as parse  # ty: ignore[import-not-found]
except ImportError:  # pragma: no cover
    import sre_parse as parse

SeedType = int | float | str | bytes | bytearray | None


class StringGenError(Exception):
    """Base exception for all string-gen errors."""


class StringGenPatternError(StringGenError):
    """
    Exception raised when an invalid regex pattern is provided.

    :param pattern: The pattern that failed to compile.
    """

    def __init__(self, pattern: re.Pattern | str | bytes, *args) -> None:  # noqa: ANN002
        super().__init__(f"Invalid pattern: {pattern!r}", *args)


class StringGenMaxIterationsReachedError(StringGenError):
    """
    Exception raised when ``render_set`` exhausts its iteration budget.

    :param max_iterations: The iteration limit that was reached.
    """

    def __init__(self, max_iterations: int, *args) -> None:  # noqa: ANN002
        super().__init__(f"Max iterations reached: {max_iterations!r}", *args)


def _build_categories(alphabet: str, printable: str) -> dict[int, str]:
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
_DEFAULT_CATEGORIES: Final[dict[int, str]] = _build_categories(string.ascii_letters, string.printable)


def _chars_in_class(items: list[tuple[int, Any]], categories: dict[int, str], printable: str) -> str:
    """
    Expand a character class, preserving order and weights for random sampling.

    :param items: Parsed items inside the character class.
    :param categories: Category lookup table.
    :param printable: Full printable character set.
    """
    negate = False
    chars: list[str] = []
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
        return "".join(sorted(set(printable) - set(chars)))
    return "".join(chars)


_DEFAULT_MAX_REPEAT: Final[int] = 100

_config: dict[str, Any] = {"max_repeat": _DEFAULT_MAX_REPEAT, "alphabet": None}


def configure(*, max_repeat: int | None = None, alphabet: str | None = None) -> None:
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


def _get_bytes(val: str | bytes) -> bytes:
    """
    Convert a string or bytes value to bytes.

    :param val: A string or bytes object to convert.
    """
    if not isinstance(val, bytes):
        return val.encode("utf-8", errors="ignore")
    return val


class _Parser:
    """Internal regex AST walker that produces random strings."""

    __slots__ = ("_class_chars", "_unique_chars", "cache", "categories", "max_repeat", "printable", "rand")

    def __init__(
        self,
        seed: SeedType = None,
        *,
        max_repeat: int = _DEFAULT_MAX_REPEAT,
        alphabet: str | None = None,
    ) -> None:
        self.cache: dict[int, str] = {}
        self._class_chars: dict[tuple[tuple[int, Any], ...], str] = {}
        self._unique_chars: dict[str, str] = {}
        self.rand = random.Random(bytes(seed) if isinstance(seed, bytearray) else seed)
        self.max_repeat = max_repeat
        if alphabet is None:
            self.categories = _DEFAULT_CATEGORIES
            self.printable = string.printable
        else:
            word = alphabet + string.digits + "_"
            self.printable = word + string.punctuation + string.whitespace
            self.categories = _build_categories(alphabet, self.printable)

    def repeat(self, start_range: int, end_range: int, value: list[Any]) -> str:
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
        if len(value) == 1:
            node = value[0]
            return "".join(self.state(node) for _ in range(times))
        return "".join(self.sequence(value) for _ in range(times))

    def group(self, value: Sequence[Any]) -> str:
        """
        Generate a capturing group and cache its result.

        :param value: Tuple of ``(group_index, ..., sub_pattern)``.
        """
        result = self.sequence(value[-1])
        if value[0]:
            self.cache[value[0]] = result
        return result

    def class_chars(self, items: list[tuple[int, Any]]) -> str:
        """Return sampling candidates for this class and instance's alphabet."""
        key = tuple(items)
        chars = self._class_chars.get(key)
        if chars is None:
            chars = self._class_chars[key] = _chars_in_class(items, self.categories, self.printable)
        return chars

    def node_chars(self, opcode: int, value: Any) -> str:
        """Return the distinct characters emitted by a single-character node."""
        if opcode == parse.IN:
            chars = self.class_chars(value)
            unique = self._unique_chars.get(chars)
            if unique is None:
                unique = self._unique_chars[chars] = "".join(sorted(set(chars)))
            return unique
        if opcode == parse.LITERAL:
            return chr(value)
        excluded = "\n" if opcode == parse.ANY else chr(value)
        return "".join(dict.fromkeys(self.printable.replace(excluded, "")))

    def state(self, state: tuple[int, Any]) -> Any:
        """
        Dispatch a single parsed opcode to its handler.

        :param state: A ``(opcode, value)`` tuple from the parsed regex AST.
        """
        opcode, value = state
        try:
            return OPCODES[opcode](self, value)
        except KeyError:
            raise StringGenError(f"Unsupported opcode: {opcode!r}") from None

    def sequence(self, parsed: Sequence[tuple[int, Any]]) -> str:
        """Render consecutive nodes using the current capture bindings."""
        return "".join(self.state(state) for state in parsed)

    def value(self, parsed: Sequence[tuple[int, Any]]) -> str:
        """Walk the parsed pattern and return a random matching string."""
        try:
            return self.sequence(parsed)
        finally:
            self.cache.clear()


# Dispatch table mapping sre_parse opcodes to handler functions.
OpcodesDict = dict[int, Callable[[_Parser, Any], Any]]

OPCODES: Final[OpcodesDict] = {
    parse.LITERAL: lambda _, x: chr(x),
    parse.NOT_LITERAL: lambda p, x: p.rand.choice(p.printable.replace(chr(x), "")),
    parse.AT: lambda *_: "",
    parse.IN: lambda p, x: p.rand.choice(p.class_chars(x)),
    parse.ANY: lambda p, _: p.rand.choice(p.printable.replace("\n", "")),
    parse.BRANCH: lambda p, x: p.sequence(p.rand.choice(x[1])),
    parse.SUBPATTERN: lambda p, x: p.group(x),
    parse.ASSERT: lambda p, x: p.sequence(x[1]),
    parse.ASSERT_NOT: lambda *_: "",
    parse.GROUPREF: lambda p, x: p.cache[x],
    parse.MIN_REPEAT: lambda p, x: p.repeat(*x),
    parse.MAX_REPEAT: lambda p, x: p.repeat(*x),
}


_CHAR_OPS = (parse.LITERAL, parse.NOT_LITERAL, parse.IN, parse.ANY)
_REPEAT_OPS = (parse.MAX_REPEAT, parse.MIN_REPEAT)


_Shape = tuple[int | None, bool]


def _branch_shape(branches: Sequence[Sequence[tuple[int, Any]]], shapes: dict[int, _Shape]) -> _Shape:
    """Distinct leading literals identify a branch from its output."""
    initials = {branch[0][1] for branch in branches if branch and branch[0][0] == parse.LITERAL}
    if len(initials) != len(branches):
        return None, True
    branch_shapes = [shapes[id(branch)] for branch in branches]
    widths = {width for width, _ in branch_shapes}
    return widths.pop() if len(widths) == 1 else None, any(overlap for _, overlap in branch_shapes)


def _delimited_repeat(body: Sequence[tuple[int, Any]], following: tuple[int, Any], parser: _Parser) -> bool:
    """Check whether the next literal marks the end of a repeated character class."""
    return (
        following[0] == parse.LITERAL
        and len(body) == 1
        and body[0][0] in _CHAR_OPS
        and chr(following[1]) not in parser.node_chars(*body[0])
    )


def _sequence_shape(nodes: Sequence[tuple[int, Any]], shapes: dict[int, _Shape], parser: _Parser) -> _Shape:
    """Combine a sequence using the already computed shapes of its children."""
    width: int | None = 0
    captures: dict[int, int | None] = {}
    open_boundary = False
    for index, (opcode, value) in enumerate(nodes):
        delimited = False
        overlap = False
        if opcode == parse.BRANCH:
            size, overlap = _branch_shape(value[1], shapes)
        elif opcode in _REPEAT_OPS:
            start, end, body = value
            size, overlap = shapes[id(body)]
            overlap = overlap or (size is None and end > 1) or (size in (None, 0) and start != end)
            size = start * size if start == end and size is not None else None
            if size is None and index + 1 < len(nodes):
                delimited = _delimited_repeat(body, nodes[index + 1], parser)
        elif opcode in (parse.SUBPATTERN, parse.ASSERT):
            size, overlap = shapes[id(value[-1])]
            if opcode == parse.SUBPATTERN and value[0]:
                captures[value[0]] = size
        elif opcode == parse.GROUPREF:
            # Only directly preceding, unconditional captures are guaranteed to be bound.
            size = captures.get(value)
        else:
            size = int(opcode in _CHAR_OPS)
        if overlap or (size is None and open_boundary):
            return None, True
        if size is None:
            open_boundary = not delimited
        width = width + size if width is not None and size is not None else None
    return width, False


def _output_shape(nodes: Sequence[tuple[int, Any]], parser: _Parser) -> _Shape:
    """Find the fixed output width and possible overlap, visiting children before parents."""
    # Collect parents before their children, then evaluate in reverse order.
    sequences = [nodes]
    for sequence in sequences:
        for opcode, value in sequence:
            if opcode == parse.BRANCH:
                sequences.extend(value[1])
            elif opcode in _REPEAT_OPS or opcode in (parse.SUBPATTERN, parse.ASSERT):
                sequences.append(value[-1])
    shapes: dict[int, _Shape] = {}
    for sequence in reversed(sequences):
        shapes[id(sequence)] = _sequence_shape(sequence, shapes, parser)
    return shapes[id(nodes)]


class _DistinctCounter:
    """Count finite regular outputs by grouping prefixes with identical continuations."""

    __slots__ = ("parser", "positions")

    def __init__(self, parser: _Parser) -> None:
        self.parser = parser
        # Position zero accepts the empty suffix.
        self.positions: list[tuple[str, frozenset[int]]] = [("", frozenset())]

    def _prepend(self, nodes: Sequence[tuple[int, Any]], tail: frozenset[int]) -> frozenset[int]:
        """Build character positions backwards, linking each to its possible successors."""
        for opcode, value in reversed(nodes):
            if opcode in _CHAR_OPS:
                self.positions.append((self.parser.node_chars(opcode, value), tail))
                tail = frozenset((len(self.positions) - 1,))
            elif opcode == parse.BRANCH:
                tail = frozenset().union(*(self._prepend(branch, tail) for branch in value[1]))
            elif opcode in (parse.SUBPATTERN, parse.ASSERT):
                tail = self._prepend(value[-1], tail)
            elif opcode in _REPEAT_OPS:
                start, end, body = value
                after_repeat = tail
                for _ in range(end - start):
                    tail = after_repeat | self._prepend(body, tail)
                for _ in range(start):
                    tail = self._prepend(body, tail)
            # AT and ASSERT_NOT emit nothing and keep the same tail.
        return tail

    def count(self, nodes: Sequence[tuple[int, Any]]) -> int:
        """Advance one character at a time, counting each distinct prefix once."""
        prefixes = {self._prepend(nodes, frozenset((0,))): 1}
        total = 0
        while prefixes:
            following: defaultdict[frozenset[int], int] = defaultdict(int)
            for positions, count in prefixes.items():
                if 0 in positions:
                    total += count
                moves: defaultdict[str, set[int]] = defaultdict(set)
                for position in positions:
                    chars, successors = self.positions[position]
                    for char in chars:
                        moves[char].update(successors)
                for destinations in moves.values():
                    following[frozenset(destinations)] += count
            prefixes = following
        return total


class _Counter:
    """Count generation paths arithmetically before resolving possible overlaps."""

    __slots__ = ("has_backrefs", "parser")

    def __init__(self, parser: _Parser) -> None:
        self.parser = parser
        self.has_backrefs = False

    def count(self, parsed: Sequence[tuple[int, Any]]) -> int | float:
        """
        Return the number of generation paths for a parsed sequence.

        :param parsed: Sequence of ``(opcode, value)`` tuples from the regex AST.
        """
        result: int | float = 1
        for node in parsed:
            factor = self._node(node)
            if factor == math.inf:
                return math.inf
            result *= factor
        return result

    def _node(self, state: tuple[int, Any]) -> int | float:
        opcode, value = state
        if opcode in _CHAR_OPS:
            return len(self.parser.node_chars(opcode, value))
        if opcode in (parse.AT, parse.ASSERT_NOT):
            return 1
        if opcode == parse.BRANCH:
            counts = [self.count(branch) for branch in value[1]]
            return math.inf if math.inf in counts else sum(counts)
        if opcode in (parse.SUBPATTERN, parse.ASSERT):
            return self.count(value[-1])
        if opcode == parse.GROUPREF:
            self.has_backrefs = True
            return 1
        if opcode in _REPEAT_OPS:
            return self._count_repeat(value)
        raise StringGenError(f"Unsupported opcode: {opcode!r}")

    def _count_repeat(self, value: tuple[int, int, list[Any]]) -> int | float:
        start, end, pattern = value
        if end >= parse.MAXREPEAT:
            return math.inf
        inner = self.count(pattern)
        if start == end:
            return 1 if start == 0 else inner**start
        if inner == math.inf:
            return math.inf
        terms = end - start + 1
        if inner == 1:
            return terms
        divisor = inner - 1
        if divisor == 1:  # Powers of two are exact bit shifts.
            return (1 << (end + 1)) - (1 << start)
        # Factor out the first term and sum 1 + inner + ... + inner**(terms - 1).
        return inner**start * ((inner**terms - 1) // divisor)


def _counted_sequence(nodes: Sequence[tuple[int, Any]]) -> Sequence[tuple[int, Any]]:
    """Strip whole-word copies: repeating each word a fixed number of times is injective."""
    while len(nodes) > 1 and nodes[0][0] == parse.SUBPATTERN:
        group, _, _, body = nodes[0][1]
        if not all(node == (parse.GROUPREF, group) for node in nodes[1:]):
            break
        nodes = body
    return nodes


@dataclass(slots=True)
class _CloseGroup:
    """Bind the output since start when a group finishes."""

    group: int
    start: int
    after: "_Cursor | _CloseGroup | None"


@dataclass(slots=True)
class _Cursor:
    """A position in a sequence and the work to resume after its last repetition."""

    nodes: Sequence[tuple[int, Any]]
    after: "_Cursor | _CloseGroup | None"
    index: int = 0
    repetitions: int = 1

    def advance(self) -> "_Cursor | _CloseGroup | None":
        """Return the continuation after the current node."""
        if self.index + 1 < len(self.nodes):
            return _Cursor(self.nodes, self.after, self.index + 1, self.repetitions)
        if self.repetitions > 1:
            return _Cursor(self.nodes, self.after, repetitions=self.repetitions - 1)
        return self.after


_Continuation = _Cursor | _CloseGroup | None
_Item = TypeVar("_Item")
_Choices = Callable[[str, int], Iterable[_Item]]
_Bindings = dict[int, tuple[int, int]]


class _Enumerator:
    """Enumerate all unique strings a parsed regex can produce."""

    __slots__ = ("max_repeat", "parser")

    def __init__(self, parser: _Parser, max_repeat: int) -> None:
        self.parser = parser
        self.max_repeat = max_repeat

    def enumerate(self, parsed: Sequence[tuple[int, Any]]) -> Iterator[str]:
        """Yield distinct strings in depth-first order, keeping choices lazy."""

        def characters(chars: str, _position: int) -> str:
            return chars

        words = map("".join, self._paths(parsed, characters))
        return self._unique(words) if _output_shape(parsed, self.parser)[1] else words

    @staticmethod
    def _unique(words: Iterator[str]) -> Iterator[str]:
        seen: set[str] = set()
        for word in words:
            if word not in seen:
                seen.add(word)
                yield word

    def count_backrefs(self, parsed: Sequence[tuple[int, Any]], needed: int | None) -> int:
        """Count structural paths with character domains and copies of captured positions."""
        domains: dict[str, frozenset[str]] = {}

        def character_domain(chars: str, position: int) -> Iterator[Atom]:
            if chars:
                if chars not in domains:
                    domains[chars] = frozenset(chars)
                yield position, domains[chars]

        return count_union(self._paths(parsed, character_domain), needed)

    def _paths(self, parsed: Sequence[tuple[int, Any]], characters: _Choices[_Item]) -> Iterator[list[_Item]]:
        """Yield a borrowed path buffer, valid until the next step of the traversal."""
        parts: list[_Item] = []
        # Each choice point resumes with the output prefix it started with.
        stack = [(0, self._steps(_Cursor(parsed, None), parts, {}, characters))]
        while stack:
            length, choices = stack[-1]
            del parts[length:]
            step = next(choices, None)
            if step is None:
                stack.pop()
                continue
            item, continuation, bindings = step
            if item is not None:
                parts.append(item)
            if continuation is not None:
                stack.append((len(parts), self._steps(continuation, parts, bindings, characters)))
            else:
                yield parts

    def _steps(  # noqa: PLR0912
        self, cursor: _Cursor | _CloseGroup, parts: list[_Item], bindings: _Bindings, characters: _Choices[_Item]
    ) -> Iterator[tuple[_Item | None, _Continuation, _Bindings]]:
        """Yield the alternatives at one position, each with its continuation."""
        if isinstance(cursor, _CloseGroup):
            yield None, cursor.after, {**bindings, cursor.group: (cursor.start, len(parts))}
            return
        if not cursor.nodes or not cursor.repetitions:
            yield None, cursor.after, bindings
            return
        opcode, value = cursor.nodes[cursor.index]
        after = cursor.advance()
        if opcode in _CHAR_OPS:
            for choice in characters(self.parser.node_chars(opcode, value), len(parts)):
                yield choice, after, bindings
        elif opcode in (parse.AT, parse.ASSERT_NOT):
            yield None, after, bindings
        elif opcode == parse.GROUPREF:
            start, end = bindings.get(value, (0, 0))
            # The choice point restores the buffer length when it backtracks.
            parts.extend(parts[start:end])
            yield None, after, bindings
        elif opcode == parse.BRANCH:
            for branch in value[1]:
                yield None, _Cursor(branch, after), bindings
        elif opcode in (parse.SUBPATTERN, parse.ASSERT):
            if opcode == parse.SUBPATTERN and value[0]:
                after = _CloseGroup(value[0], len(parts), after)
            yield None, _Cursor(value[-1], after), bindings
        elif opcode in _REPEAT_OPS:
            start, end, body = value
            upper = end if end < parse.MAXREPEAT else max(start, self.max_repeat)
            for count in range(start, upper + 1):
                yield None, _Cursor(body, after, repetitions=count), bindings
        else:
            raise StringGenError(f"Unsupported opcode: {opcode!r}")


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

    __slots__ = ("_cached_count", "_parser", "_pattern", "_tree")
    __hash__ = None

    def __init__(
        self,
        pattern: re.Pattern | str | bytes,
        seed: SeedType = None,
        *,
        max_repeat: int | None = None,
        alphabet: str | None = None,
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
        self._tree: Sequence[tuple[int, Any]] | None = None
        self._cached_count: int | float | None = None

    @property
    def _parsed(self) -> Sequence[tuple[int, Any]]:
        if self._tree is None:
            # re.compile already emitted any requested debug output.
            flags = self._pattern.flags & ~int(re.DEBUG)
            self._tree = parse.parse(self._pattern.pattern, flags).data
        return self._tree

    @property
    def pattern(self) -> re.Pattern:
        """Compiled ``re.Pattern`` object used for generation."""
        return self._pattern

    def __get_value(self, value: object) -> re.Pattern:
        if isinstance(value, type(self)):
            return value._pattern  # noqa: SLF001
        if isinstance(value, re.Pattern):
            return value
        if isinstance(value, (str, bytes)):
            return re.compile(value)
        raise TypeError(f"Unexpected type {type(value)!r} The only supported: str, StringGen, re.Pattern")

    def __eq__(self, other: object) -> bool:
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
        self._parser.rand.seed(bytes(seed) if isinstance(seed, bytearray) else seed)

    def render(self) -> str:
        """Produce a single random string matching the pattern."""
        return self._parser.value(self._parsed)

    def count(self) -> int | float:
        """
        Return the number of unique strings the pattern can produce.

        Returns ``math.inf`` for patterns with unbounded quantifiers
        (``*``, ``+``, ``{n,}``).  The result is cached after the first call.
        """
        return self._available()

    def _available(self, needed: int | None = None) -> int | float:
        """Cache the exact count, or stop an exhaustive search once enough strings exist."""
        if self._cached_count is not None:
            return self._cached_count
        nodes = _counted_sequence(self._parsed)
        counter = _Counter(self._parser)
        total = counter.count(nodes)
        if total != math.inf and _output_shape(nodes, self._parser)[1]:
            if counter.has_backrefs:
                total = _Enumerator(self._parser, self._parser.max_repeat).count_backrefs(nodes, needed)
                if needed is not None and total >= needed:
                    return total
            else:
                total = _DistinctCounter(self._parser).count(nodes)
        self._cached_count = total
        return total

    def enumerate(self, *, limit: int | None = None) -> Iterator[str]:
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
        enumerator = _Enumerator(self._parser, effective_limit)
        yield from enumerator.enumerate(self._parsed)

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

    def render_list(self, count: int) -> list[str]:
        """
        Produce a list of random strings matching the pattern.

        :param count: Number of strings to generate.
        """
        if count < 0:
            raise ValueError(f"count must be >= 0, got {count}")
        return [self.render() for _ in range(count)]

    def render_set(self, count: int, *, max_iteration: int = 100_000) -> set[str]:
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
        if count == 0:
            return set()
        available = self._available(needed=count) if type(self) is StringGen else self.count()
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
