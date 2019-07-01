import pytest

from dataclasses import dataclass
from typing import Union, List

from hologram import JsonSchemaMixin, ValidationError, NewPatternProperty


@dataclass
class Foo(JsonSchemaMixin):
    a: str
    b: int


Bar = NewPatternProperty(Foo)

Baz = NewPatternProperty(Union[Foo, List[Foo], str])


@dataclass
class Container(JsonSchemaMixin):
    bar: Bar
    baz: Baz


@pytest.fixture
def foo():
    return Foo("one", 1)


@pytest.fixture
def foo_dict():
    return {"a": "one", "b": 1}


@pytest.fixture
def bar():
    b = Bar()
    b["first"] = Foo("one", 1)
    b["second"] = Foo("two", 2)
    return b


@pytest.fixture
def bar_dict():
    return {"first": {"a": "one", "b": 1}, "second": {"a": "two", "b": 2}}


@pytest.fixture
def wrong_interior_dict():
    return {"first": {"a": "one", "b": 1}, "second": {"a": "two", "b": "2"}}


@pytest.fixture
def baz():
    b = Baz()
    b["first"] = Foo("one", 1)
    b["second"] = [Foo("two", 2)]
    b["third"] = "three"
    return b


@pytest.fixture
def baz_dict():
    return {
        "first": {"a": "one", "b": 1},
        "second": [{"a": "two", "b": 2}],
        "third": "three",
    }


@pytest.fixture
def container(bar, baz):
    return Container(bar=bar, baz=baz)


@pytest.fixture
def container_dict(bar_dict, baz_dict):
    return {"bar": bar_dict, "baz": baz_dict}


@pytest.fixture
def inverted_container_dict(bar_dict, baz_dict):
    return {"bar": baz_dict, "baz": bar_dict}


def test_mapping(bar, bar_dict, wrong_interior_dict):
    assert Bar.from_dict(bar_dict) == bar
    assert bar.to_dict() == bar_dict

    with pytest.raises(ValidationError):
        Bar.from_dict(wrong_interior_dict)


def test_complex_mapping(baz, baz_dict, wrong_interior_dict):
    assert Baz.from_dict(baz_dict) == baz
    assert baz.to_dict() == baz_dict

    with pytest.raises(ValidationError):
        Baz.from_dict(wrong_interior_dict)


def test_contains_mapping(container, container_dict, inverted_container_dict):
    assert Container.from_dict(container_dict) == container
    assert container.to_dict() == container_dict

    with pytest.raises(ValidationError):
        Container.from_dict(inverted_container_dict)
