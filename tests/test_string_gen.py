"""Module tests."""

import random
import re
from typing import Callable, Union

import pytest

from string_gen import (
    StringGen,
    StringGenMaxIterationsReachedError,
    StringGenPatternError,
)

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
    with pytest.raises(KeyError):
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


def test_render_set_error():
    gen = StringGen(r"\d")
    with pytest.raises(StringGenMaxIterationsReachedError):
        gen.render_set(count=11, max_iteration=2)


def test_set_seed():
    gen = StringGen(r"\d", seed=b"12")
    values = set(gen.render_list(count=10))
    assert len(values) == 8


def test_set_seed_method():
    gen = StringGen(r"\d")
    gen.seed(b"12")
    values = set(gen.render_list(count=10))
    assert len(values) == 8


@pytest.mark.parametrize("regex", (r"\d", rb"\d"))
@pytest.mark.parametrize("mode", ("str", "sting_gen", "pattern"))
def test_equal(mode: str, regex: Union[str, bytes]):
    new_regex = regex
    if mode == "pattern":
        new_regex = re.compile(regex)
    elif mode == "sting_gen":
        new_regex = StringGen(regex)
    assert StringGen(regex) == new_regex


def test_equal_error():
    gen = StringGen(r"\d")
    with pytest.raises(TypeError):
        assert gen == 1


@pytest.mark.parametrize("regex", (r"\d", rb"\d"))
@pytest.mark.parametrize("mode", ("str", "sting_gen", "pattern"))
def test_not_equal(mode: str, regex: Union[str, bytes]):
    new_regex = regex
    if mode == "pattern":
        new_regex = re.compile(regex)
    elif mode == "sting_gen":
        new_regex = StringGen(regex)
    assert StringGen(r"\w") != new_regex


def test_bool():
    assert not StringGen("")
    assert StringGen("[1]+")


def test_or():
    gen1 = StringGen(r"^\d$")
    gen2 = StringGen(rb"^\w$")
    gen1 |= gen2
    assert re.match(r"^\d\w$", gen1.render())


@pytest.mark.parametrize("func", (str, repr))
def test_str_repr(func: Callable[[StringGen], str]):
    regex = r"^\d$"
    assert func(StringGen(regex)) == f"{StringGen.__name__}({regex!r})"
