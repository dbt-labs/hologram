import pytest

from dataclasses import dataclass
from typing import NewType

from hologram import ValidationError, JsonSchemaMixin
from hologram.helpers import register_pattern


Uppercase = NewType("Uppercase", str)
register_pattern(Uppercase, r"[A-Z]+")


@dataclass
class Loud(JsonSchemaMixin):
    shouting: Uppercase
    normal: str


@pytest.fixture
def loud():
    return Loud(shouting="SHOUTING", normal="Normal")


@pytest.fixture
def loud_dict():
    return {"shouting": "SHOUTING", "normal": "Normal"}


@pytest.fixture
def too_quiet():
    return {"shouting": "shhhhh", "normal": "Normal"}


def test_loud(loud, loud_dict, too_quiet):
    assert loud.to_dict() == loud_dict
    assert Loud.from_dict(loud_dict) == loud

    with pytest.raises(ValidationError):
        Loud.from_dict(too_quiet)
