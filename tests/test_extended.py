import pytest

from dataclasses import dataclass

from hologram import ValidationError, JsonSchemaMixin
from hologram.helpers import ExtensibleJsonSchemaMixin


@dataclass
class Extensible(ExtensibleJsonSchemaMixin):
    a: str
    b: int


@dataclass
class Inextensible(JsonSchemaMixin):
    a: str
    b: int


@pytest.fixture
def extensible_dict():
    return {"a": "one", "b": 1}


@pytest.fixture
def extra_data(extensible_dict):
    extra = dict(extensible_dict)
    extra["c"] = []
    return extra


@pytest.fixture
def extensible():
    return Extensible(a="one", b=1)


@pytest.fixture
def inextensible():
    return Inextensible(a="one", b=1)


def test_extensible(extra_data, extensible_dict, extensible):
    assert Extensible.from_dict(extra_data) == extensible
    assert Extensible.from_dict(extensible_dict) == extensible
    assert extensible.to_dict() == extensible_dict
    assert Extensible.from_dict(extra_data).to_dict() == extensible_dict


def test_inextensible(extra_data, extensible_dict, inextensible):
    assert Inextensible.from_dict(extensible_dict) == inextensible
    assert inextensible.to_dict() == extensible_dict
    with pytest.raises(ValidationError):
        Inextensible.from_dict(extra_data)
