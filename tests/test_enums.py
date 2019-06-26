import pytest

from dataclasses import dataclass
from hologram import JsonSchemaMixin, ValidationError
from hologram.helpers import StrEnum, StrLiteral
from typing import List


class Bar(StrEnum):
    x = "x"
    y = "y"


@dataclass
class UsesBar(JsonSchemaMixin):
    bar: Bar


@dataclass
class UsesBarLiteral(JsonSchemaMixin):
    bar: StrLiteral(Bar.x)


def test_symmetry():
    def assert_symmetry(value):
        assert UsesBar.from_dict(value).to_dict() == value

    assert_symmetry({"bar": "x"})
    assert_symmetry({"bar": "y"})


def test_validation():
    with pytest.raises(ValidationError):
        UsesBar.from_dict({"bar": "invalid"})

    with pytest.raises(ValidationError):
        UsesBarLiteral.from_dict({"bar": "y"})


def test_schema():
    schema = UsesBar.json_schema()

    assert schema["type"] == "object"
    assert schema["required"] == ["bar"]
    assert schema["properties"] == {
        "bar": {"type": "string", "enum": ["x", "y"]}
    }

    schema = UsesBarLiteral.json_schema()

    assert schema["type"] == "object"
    assert schema["required"] == ["bar"]
    assert schema["properties"] == {"bar": {"type": "string", "enum": ["x"]}}
