from hologram import FieldEncoder, JsonSchemaMixin, ValidationError

import pytest

from dataclasses import dataclass
from typing import NewType, List, Union


ListOrTuple = NewType("ListOrTuple", List[str])


class ListOrTupleEncoder(FieldEncoder):
    def to_wire(self, value):
        return list(value)

    def to_python(self, value):
        return value

    @property
    def json_schema(self):
        return {"type": "array", "items": {"type": "string"}}


class ListOrTupleOrAloneEncoder(FieldEncoder):
    def to_wire(self, value):
        if isinstance(value, (tuple, list)):
            return list(value)
        else:
            return [value]

    def to_python(self, value):
        if isinstance(value, (tuple, list)):
            return list(value)
        else:
            return [value]

    @property
    def json_schema(self):
        return {"type": ["array", "string"], "items": {"type": "string"}}


JsonSchemaMixin.register_field_encoders(
    {
        ListOrTuple: ListOrTupleEncoder(),
        Union[ListOrTuple, str]: ListOrTupleOrAloneEncoder(),
        Union[str, ListOrTuple]: ListOrTupleOrAloneEncoder(),
    }
)


@dataclass
class Foo(JsonSchemaMixin):
    thing: Union[ListOrTuple, str]


def test_registered():
    first = Foo(thing="one")
    second = Foo(thing=["two", "2"])
    third = Foo(thing=("three", "3"))

    assert first.to_dict() == {"thing": ["one"]}
    assert Foo.from_dict({"thing": "one"}) == Foo(thing=["one"])

    assert second.to_dict() == {"thing": ["two", "2"]}
    assert Foo.from_dict({"thing": ["two", "2"]}) == second

    assert third.to_dict() == {"thing": ["three", "3"]}
    # dicts must be valid json
    with pytest.raises(ValidationError):
        Foo.from_dict({"thing": ("three", "3")})
