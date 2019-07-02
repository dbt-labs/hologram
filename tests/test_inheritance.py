import pytest

from dataclasses import dataclass
from hologram import JsonSchemaMixin, ValidationError
from hologram.helpers import StrEnum, StrLiteral
from typing import Optional, Union, List


class Stage(StrEnum):
    one = "one"
    two = "two"


@dataclass
class StageOneFoo(JsonSchemaMixin):
    unique_id: str = None
    stage: StrLiteral(Stage.one) = Stage.one
    has_default: Optional[str] = None


@dataclass
class StageTwoFoo(StageOneFoo, JsonSchemaMixin):
    additional_information: str = None
    stage: StrLiteral(Stage.two) = Stage.two
    additional_default: Optional[int] = None


def test_symmetry_StageOneFoo():
    def assert_symmetry_StageOne(value):
        assert StageOneFoo.from_dict(value).to_dict() == value

    assert_symmetry_StageOne({"unique_id": "abc", "stage": "one"})


def test_symmetry_StageTwoFoo():
    def assert_symmetry_StageTwo(value):
        assert StageTwoFoo.from_dict(value).to_dict() == value

    assert_symmetry_StageTwo(
        {"unique_id": "abc", "stage": "two", "additional_information": "def"}
    )


def test_wrong_class():
    with pytest.raises(ValidationError):
        StageOneFoo.from_dict(
            {
                "unique_id": "abc",
                "stage": "two",
                "additional_information": "def",
            }
        )


def test_inferred_class():
    assert isinstance(
        JsonSchemaMixin.from_dict(
            {
                "unique_id": "abc",
                "stage": "two",
                "additional_information": "def",
            }
        ),
        StageTwoFoo,
    )


@dataclass
class Thing(JsonSchemaMixin):
    a: str


@dataclass
class OtherThing(JsonSchemaMixin):
    b: str
    c: str


@dataclass
class MoreThings(JsonSchemaMixin):
    d: str
    e: str


@dataclass
class Unioned(JsonSchemaMixin):
    unioned: List[Union[Thing, OtherThing, MoreThings]]


@dataclass
class Nested(JsonSchemaMixin):
    first: Thing
    top: List[Union[List[Thing], Thing, OtherThing, List[MoreThings]]]


def test_tricky_unions():
    dcts = {
        "unioned": [
            {"a": "Thing"},
            {"b": "hi", "c": "OtherThing"},
            {"a": "Thing2"},
        ]
    }
    expected = [
        Thing(a="Thing"),
        OtherThing(b="hi", c="OtherThing"),
        Thing(a="Thing2"),
    ]
    assert Unioned.from_dict(dcts).unioned == expected
    assert Unioned.from_dict(dcts).to_dict() == dcts


def test_nested_ok():
    nested = {
        "first": {"a": "Thing"},
        "top": [
            [{"a": "Thing"}],
            {"a": "Thing"},
            {"b": "OtherThing", "c": "stuff"},
            [{"d": "MoreThings", "e": "more stuff"}],
        ],
    }
    expected = [
        [Thing(a="Thing")],
        Thing(a="Thing"),
        OtherThing(b="OtherThing", c="stuff"),
        [MoreThings(d="MoreThings", e="more stuff")],
    ]
    result = Nested.from_dict(nested)
    assert result.top == expected
    assert result.first == Thing(a="Thing")

    assert Nested.from_dict(nested).to_dict() == nested


def test_bad_nested():
    bad_nested = {
        "first": {"a": "Thing"},
        "top": [
            [{"a": 1}],
            {"a": "Thing"},
            {"b": "OtherThing", "c": "stuff"},
            [{"d": "MoreThings", "e": "more stuff"}],
        ],
    }
    with pytest.raises(ValidationError):
        Nested.from_dict(bad_nested)

    bad_nested_2 = {
        "first": {"a": 1},
        "top": [
            [{"a": "Thing"}],
            {"a": "Thing"},
            {"b": "OtherThing", "c": "stuff"},
            [{"d": "MoreThings", "e": "more stuff"}],
        ],
    }
    with pytest.raises(ValidationError):
        Nested.from_dict(bad_nested)
