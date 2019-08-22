import pytest

from dataclasses import dataclass, field
from typing import Union

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
class HasRestricted(JsonSchemaMixin):
    thing: Union[RestrictAB, int, RestrictC]


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


@dataclass
class FancyRestrictBase(JsonSchemaMixin):
    foo: MySelector


@dataclass
class FancyRestrictATrue(FancyRestrictBase):
    foo: MySelector = field(metadata={"restrict": [MySelector.A]})
    is_something: bool = field(metadata={"restrict": [True]})
    bar: str


@dataclass
class FancyRestrictAFalse(FancyRestrictBase):
    foo: MySelector = field(metadata={"restrict": [MySelector.A]})
    is_something: bool = field(metadata={"restrict": [False]})
    bar: str


@dataclass
class FancyRestrictBC(FancyRestrictBase):
    foo: MySelector = field(
        metadata={"restrict": [MySelector.B, MySelector.C]}
    )
    bar: str


@dataclass
class HasFancyRestricted(JsonSchemaMixin):
    thing: Union[FancyRestrictATrue, FancyRestrictAFalse, FancyRestrictBC]


def test_multi_symmetric():
    x = HasFancyRestricted(
        thing=FancyRestrictATrue(
            foo=MySelector.A, is_something=True, bar="a and true"
        )
    )
    x_dict = {"thing": {"foo": "a", "is_something": True, "bar": "a and true"}}
    assert x.to_dict(validate=True) == x_dict
    assert HasFancyRestricted.from_dict(x_dict, validate=True) == x

    y = HasFancyRestricted(
        thing=FancyRestrictAFalse(
            foo=MySelector.A, is_something=False, bar="a and false"
        )
    )
    y_dict = {
        "thing": {"foo": "a", "is_something": False, "bar": "a and false"}
    }
    assert y.to_dict() == y_dict
    assert HasFancyRestricted.from_dict(y_dict) == y

    z = HasFancyRestricted(
        thing=FancyRestrictBC(foo=MySelector.C, bar="c and nothing")
    )
    z_dict = {"thing": {"foo": "c", "bar": "c and nothing"}}
    assert z.to_dict() == z_dict
    assert HasFancyRestricted.from_dict(z_dict) == z

    # test the non-unioned forms, too!
    assert x.thing.to_dict() == x_dict["thing"]
    assert FancyRestrictATrue.from_dict(x_dict["thing"]) == x.thing
    # test the non-unioned forms, too!
    assert y.thing.to_dict() == y_dict["thing"]
    assert FancyRestrictAFalse.from_dict(y_dict["thing"]) == y.thing
    # test the non-unioned forms, too!
    assert z.thing.to_dict() == z_dict["thing"]
    assert FancyRestrictBC.from_dict(z_dict["thing"]) == z.thing


def test_json_schema_ok():
    schema = HasFancyRestricted.json_schema()
    assert schema["additionalProperties"] is False
    assert schema["properties"] == {
        "thing": {
            "oneOf": [
                {"$ref": "#/definitions/FancyRestrictATrue"},
                {"$ref": "#/definitions/FancyRestrictAFalse"},
                {"$ref": "#/definitions/FancyRestrictBC"},
            ]
        }
    }
    assert schema["required"] == ["thing"]

    for k in "FancyRestrictATrue", "FancyRestrictAFalse", "FancyRestrictBC":
        assert k in schema["definitions"]
        assert schema["definitions"][k]["additionalProperties"] is False
    assert schema["definitions"]["FancyRestrictATrue"]["type"] == "object"

    assert schema["definitions"]["FancyRestrictATrue"]["properties"] == {
        "foo": {"enum": ["a"], "type": "string"},
        "is_something": {"enum": [True], "type": "boolean"},
        "bar": {"type": "string"},
    }
    assert sorted(schema["definitions"]["FancyRestrictATrue"]["required"]) == [
        "bar",
        "foo",
        "is_something",
    ]
    assert schema["definitions"]["FancyRestrictAFalse"]["properties"] == {
        "foo": {"enum": ["a"], "type": "string"},
        "is_something": {"enum": [False], "type": "boolean"},
        "bar": {"type": "string"},
    }
    assert sorted(
        schema["definitions"]["FancyRestrictAFalse"]["required"]
    ) == ["bar", "foo", "is_something"]

    schema["definitions"]["FancyRestrictBC"]["properties"]["foo"][
        "enum"
    ].sort()
    assert schema["definitions"]["FancyRestrictBC"]["properties"] == {
        "foo": {"enum": ["b", "c"], "type": "string"},
        "bar": {"type": "string"},
    }
    assert sorted(schema["definitions"]["FancyRestrictBC"]["required"]) == [
        "bar",
        "foo",
    ]


class OtherSelector(StrEnum):
    X = "x"
    Y = "y"
    Z = "z"


@dataclass
class InvalidRestrictedType(JsonSchemaMixin):
    foo: MySelector = field(metadata={"restrict": [MySelector.A, int]})


def test_bad_restrictions():
    with pytest.raises(ValidationError):
        InvalidRestrictedType.json_schema()
