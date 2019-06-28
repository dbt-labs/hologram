import pytest

from dataclasses import dataclass, field
from hologram import JsonSchemaMixin, ValidationError
from hologram.helpers import HyphenatedJsonSchemaMixin


@dataclass
class HasUnderscoreConverts(HyphenatedJsonSchemaMixin):
    a_thing: str = field(metadata={"preserve_underscore": True})
    other_thing: str


@dataclass
class ContainsHasUnderscoreConverts(JsonSchemaMixin):
    things: HasUnderscoreConverts


@pytest.fixture
def underscore():
    return HasUnderscoreConverts(a_thing="foo", other_thing="bar")


@pytest.fixture
def underscore_dict():
    return {"a_thing": "foo", "other-thing": "bar"}


@pytest.fixture
def contains(underscore):
    return ContainsHasUnderscoreConverts(things=underscore)


@pytest.fixture
def contains_dict(underscore_dict):
    return {"things": underscore_dict}


@pytest.fixture
def bad_dict():
    return {"a_thing": "foo", "other_thing": "bar"}


def test_base(underscore, underscore_dict, bad_dict):
    assert HasUnderscoreConverts.from_dict(underscore_dict) == underscore
    assert underscore.to_dict() == underscore_dict

    with pytest.raises(ValidationError):
        HasUnderscoreConverts.from_dict(bad_dict)


def test_nested(contains, contains_dict, bad_dict):
    assert ContainsHasUnderscoreConverts.from_dict(contains_dict) == contains
    assert contains.to_dict() == contains_dict

    with pytest.raises(ValidationError):
        ContainsHasUnderscoreConverts.from_dict({"things": bad_dict})
