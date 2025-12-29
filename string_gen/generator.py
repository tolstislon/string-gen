"""String generator."""

import random
import re
import string
from itertools import chain
from typing import Any, AnyStr, Callable, Dict, Final, List, Sequence, Set, Tuple, Union

try:
    import re._parser as parse
except ImportError:  # pragma: no cover
    import sre_parse as parse

SeedType = Union[int, float, str, bytes, bytearray, None]


class StringGenError(Exception):
    """Base class for exceptions in this module."""


class StringGenPatternError(StringGenError):
    """Exception raised for errors in the input."""

    def __init__(self, pattern: Union[re.Pattern, AnyStr], *args) -> None:  # noqa: ANN002
        super().__init__(f"Invalid pattern: {pattern!r}", *args)


class StringGenMaxIterationsReachedError(StringGenError):
    """Max iterations reached."""

    def __init__(self, max_iterations: int, *args) -> None:  # noqa: ANN002
        super().__init__(f"Max iterations reached: {max_iterations!r}", *args)


CATEGORIES: Final[Dict[int, str]] = {
    parse.CATEGORY_DIGIT: string.digits,
    parse.CATEGORY_NOT_DIGIT: string.ascii_letters + string.punctuation,
    parse.CATEGORY_SPACE: string.whitespace,
    parse.CATEGORY_NOT_SPACE: string.printable.strip(),
    parse.CATEGORY_WORD: string.ascii_letters + string.digits + "_",
    parse.CATEGORY_NOT_WORD: "".join(set(string.printable).difference(string.ascii_letters + string.digits + "_")),
}


def _get_bytes(val: AnyStr) -> bytes:
    if not isinstance(val, bytes):
        return val.encode("utf-8", errors="ignore")
    return val


class _Parser:
    __slots__ = ("cache", "rand")

    def __init__(self, seed: SeedType = None) -> None:
        self.cache: Dict[str, Any] = {}
        self.rand = random.Random(seed)

    def repeat(self, start_range: int, end_range: int, value: List[Any]) -> str:
        times = self.rand.randint(start_range, min((end_range, 100)))
        return "".join("".join(self.state(i) for i in value) for _ in range(times))

    def group(self, value: Sequence[Any]) -> str:
        result = "".join(self.state(i) for i in value[-1])
        if value[0]:
            self.cache[value[0]] = result
        return result

    def in_state(self, value: List[Any]) -> Any:
        candidates = list(chain(*(self.state(i) for i in value)))
        if candidates[0] is False:
            candidates = list(set(string.printable).difference(candidates[1:]))
        return self.rand.choice(candidates)

    def state(self, state: Tuple[int, Any]) -> Any:
        opcode, value = state
        return OPCODES[opcode](self, value)

    def value(self, pattern: re.Pattern) -> str:
        parsed = parse.parse(pattern.pattern)
        result = "".join(self.state(state) for state in parsed)
        self.cache.clear()
        return result


OpcodesDict = Dict[int, Callable[[_Parser, Any], Any]]

OPCODES: Final[OpcodesDict] = {
    parse.LITERAL: lambda _, x: chr(x),
    parse.NOT_LITERAL: lambda p, x: p.rand.choice(string.printable.replace(chr(x), "")),
    parse.AT: lambda *_: "",
    parse.IN: lambda p, x: p.in_state(x),
    parse.ANY: lambda p, _: p.rand.choice(string.printable.replace("\n", "")),
    parse.RANGE: lambda _, x: [chr(i) for i in range(x[0], x[1] + 1)],
    parse.CATEGORY: lambda _, x: CATEGORIES[x],
    parse.BRANCH: lambda p, x: "".join(p.state(i) for i in p.rand.choice(x[1])),
    parse.SUBPATTERN: lambda p, x: p.group(x),
    parse.ASSERT: lambda p, x: "".join(p.state(i) for i in x[1]),
    parse.ASSERT_NOT: lambda *_: "",
    parse.GROUPREF: lambda p, x: p.cache[x],
    parse.MIN_REPEAT: lambda p, x: p.repeat(*x),
    parse.MAX_REPEAT: lambda p, x: p.repeat(*x),
    parse.NEGATE: lambda *_: [False],
}


class StringGen:  # noqa: PLW1641
    """Base class for generating strings."""

    __slots__ = ("_parser", "_pattern")

    def __init__(self, pattern: Union[re.Pattern, AnyStr], seed: SeedType = None) -> None:
        try:
            self._pattern: re.Pattern = re.compile(pattern)
        except re.error as error:
            raise StringGenPatternError(pattern) from error
        self._parser = _Parser(seed)

    @property
    def pattern(self) -> re.Pattern:
        """Return pattern."""
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

    def __ne__(self, other: Union[re.Pattern, "StringGen", AnyStr]) -> bool:
        return self._pattern != self.__get_value(other)

    def __bool__(self) -> bool:
        return bool(self._pattern.pattern)

    def __or__(self, other: "StringGen") -> "StringGen":
        base = _get_bytes(self._pattern.pattern)
        other = _get_bytes(self.__get_value(other).pattern)
        return StringGen(base.rstrip(b"^") + other.lstrip(b"$"))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._pattern.pattern!r})"

    def seed(self, seed: SeedType = None) -> None:
        """Initialize internal state from a seed."""
        self._parser.rand.seed(seed)

    def render(self) -> str:
        """Produce a random string that fits the pattern."""
        return self._parser.value(self._pattern)

    def render_list(self, count: int) -> List[str]:
        """Return a list of generated strings."""
        return [self.render() for _ in range(count)]

    def render_set(self, count: int, *, max_iteration: int = 100_000) -> Set[str]:
        """Return a set of generated unique strings."""
        max_iteration = max(count, max_iteration)
        values = set()
        iterations = 0
        while len(values) < count and iterations < max_iteration:
            values.add(self.render())
            iterations += 1
        if iterations >= max_iteration and len(values) != count:
            raise StringGenMaxIterationsReachedError(max_iteration)
        return values
