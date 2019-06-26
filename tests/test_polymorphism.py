import pytest

from dataclasses import dataclass
from hologram import JsonSchemaMixin, ValidationError
from hologram.helpers import StrEnum, StrLiteral
from typing import Union


class Bar(StrEnum):
    x = "x"
    y = "y"


@dataclass
class BarX(JsonSchemaMixin):
    bar: StrLiteral(Bar.x)


@dataclass
class BarY(JsonSchemaMixin):
    bar: StrLiteral(Bar.y)


@dataclass
class Foo(JsonSchemaMixin):
    foo: Union[BarX, BarY]


def test_symmetry():
    def assert_symmetry(value):
        assert Foo.from_dict(value).to_dict() == value

    assert_symmetry({"foo": {"bar": "x"}})
    assert_symmetry({"foo": {"bar": "y"}})


def test_subclasses():
    foo_x = Foo.from_dict({"foo": {"bar": "x"}})
    assert isinstance(foo_x.foo, BarX)

    foo_y = Foo.from_dict({"foo": {"bar": "y"}})
    assert isinstance(foo_y.foo, BarY)
