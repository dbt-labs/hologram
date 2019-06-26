import pytest

from dataclasses import dataclass, field, MISSING
from hologram import JsonSchemaMixin, ValidationError
from hologram.helpers import StrEnum, StrLiteral
from typing import Optional


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
