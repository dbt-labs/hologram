import pytest

from dataclasses import dataclass, field
from typing import Union, NewType, Optional

from hologram import JsonSchemaMixin, ValidationError
from hologram.helpers import StrEnum


class MySelector(StrEnum):
    A = "a"
    B = "b"
    C = "c"


@dataclass
class RestrictAB(JsonSchemaMixin):
    foo: MySelector = field(
        metadata={"restrict": [MySelector.A, MySelector.B]}
    )
    bar: int


@dataclass
class RestrictC(JsonSchemaMixin):
    foo: MySelector = field(metadata={"restrict": [MySelector.C]})
    baz: str

@dataclass
class A(JsonSchemaMixin):
    baz: str

@dataclass
class B(JsonSchemaMixin):
    baz: str


@dataclass
class HasRestricted(JsonSchemaMixin):
    thing: Union[A, Optional[Union[RestrictAB, RestrictC]], B]


def test_encode():
    x = HasRestricted(thing=RestrictAB(foo=MySelector.A, bar=20))
    assert x.to_dict() == {"thing": {"foo": "a", "bar": 20}}

    y = HasRestricted(thing=1000)
    assert y.to_dict() == {"thing": 1000}

    z = HasRestricted(thing=RestrictC(foo=MySelector.C, baz="hi"))
    assert z.to_dict() == {"thing": {"foo": "c", "baz": "hi"}}

    with pytest.raises(ValidationError):
        x = HasRestricted(thing=RestrictAB(foo=MySelector.C, bar=20))
        x.to_dict(validate=True)


def test_decode():
    x = HasRestricted(thing=RestrictAB(foo=MySelector.A, bar=20))
    assert (
        HasRestricted.from_dict(
            {"thing": {"foo": "a", "bar": 20}}, validate=True
        )
        == x
    )

    with pytest.raises(ValidationError):
        HasRestricted.from_dict(
            {"thing": {"foo": "c", "baz": 20}}, validate=True
        )
