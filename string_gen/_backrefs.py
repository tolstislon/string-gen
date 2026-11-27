"""Count unions of fixed-length character constraints for finite backreferences."""

from collections import defaultdict
from collections.abc import Iterable, Sequence
from math import prod

# Each position names its first occurrence and the characters it may take.
Atom = tuple[int, frozenset[str]]
_Template = tuple[Atom, ...]


def _intersection(left: _Template, right: _Template) -> _Template | None:
    """Combine the equality constraints and allowed characters of both templates."""
    parents = list(range(len(left)))
    domains = [chars for _, chars in left]

    def root(index: int) -> int:
        while index != parents[index]:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    for index, ((left_pos, _), (right_pos, chars)) in enumerate(zip(left, right, strict=True)):
        # Both representatives precede or equal index. Keep the earliest one.
        a, b = root(left_pos), root(right_pos)
        first, last = min(a, b), max(a, b)
        allowed = domains[first] & domains[last] & domains[index] & chars
        if not allowed:
            return None
        parents[last] = parents[index] = first
        domains[first] = allowed

    result = []
    for index in range(len(left)):
        first = root(index)
        chars = domains[first]
        result.append((index if len(chars) == 1 else first, chars))
    return tuple(result)


def count_union(paths: Iterable[Sequence[Atom]], needed: int | None) -> int:
    """Count distinct assignments, stopping at a sufficient lower bound if requested."""
    by_length: defaultdict[int, dict[_Template, int]] = defaultdict(dict)
    total = 0
    for path in paths:
        template = tuple((i if len(chars) == 1 else first, chars) for i, (first, chars) in enumerate(path))
        terms = by_length[len(template)]
        if template in terms:
            continue

        # Add the new template and subtract its intersections with the existing union.
        changes: defaultdict[_Template, int] = defaultdict(int)
        changes[template] = 1
        for other, coefficient in terms.items():
            common = _intersection(template, other)
            if common == template:
                break  # This term already contains the entire new template.
            if common is not None:
                changes[common] -= coefficient
        else:
            for member, coefficient in changes.items():
                total += coefficient * prod(len(chars) for i, (first, chars) in enumerate(member) if i == first)
                weight = terms.get(member, 0) + coefficient
                if weight:
                    terms[member] = weight
                else:
                    terms.pop(member, None)
            if needed is not None and total >= needed:
                break
    return total
