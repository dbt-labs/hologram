import pytest

from dataclasses import dataclass
from typing import Union, Optional, List

from hologram import JsonSchemaMixin, ValidationError


@dataclass
class IHaveAnnoyingUnions(JsonSchemaMixin):
    my_field: Optional[Union[List[str], str]]


@dataclass
class IHaveAnnoyingUnionsReversed(JsonSchemaMixin):
    my_field: Optional[Union[str, List[str]]]


def test_union_decoding():
    for field_value in (None, [">=0.0.0"], ">=0.0.0"):
        obj = IHaveAnnoyingUnions(my_field=field_value)
        dct = {"my_field": field_value}
        decoded = IHaveAnnoyingUnions.from_dict(dct)
        assert decoded == obj
        assert obj.to_dict(omit_none=False) == dct

    # this is allowed, for backwards-compatibility reasons
    IHaveAnnoyingUnions(my_field=(">=0.0.0",)) == {"my_field": (">=0.0.0",)}


def test_union_decoding_ordering():
    for field_value in (None, [">=0.0.0"], ">=0.0.0"):
        obj = IHaveAnnoyingUnionsReversed(my_field=field_value)
        dct = {"my_field": field_value}
        decoded = IHaveAnnoyingUnionsReversed.from_dict(dct)
        assert decoded == obj
        assert obj.to_dict(omit_none=False) == dct

    # this is allowed, for backwards-compatibility reasons
    IHaveAnnoyingUnionsReversed(my_field=(">=0.0.0",)) == {
        "my_field": (">=0.0.0",)
    }


def test_union_decode_error():
    x = IHaveAnnoyingUnions(my_field={">=0.0.0"})
    with pytest.raises(ValidationError):
        x.to_dict(validate=True)

    with pytest.raises(ValidationError):
        IHaveAnnoyingUnions.from_dict({"my_field": {">=0.0.0"}})


@dataclass
class UnionMember(JsonSchemaMixin):
    a: int


@dataclass
class LongOptionalUnion(JsonSchemaMixin):
    # this devolves into Union[None, UnionMember]
    member: Optional[Union[None, UnionMember]]


def test_long_union_decoding():
    x = LongOptionalUnion(None)
    x.to_dict() == {"member": None}
    LongOptionalUnion.from_dict({"member": None})

    x = LongOptionalUnion(UnionMember(1))
    x.to_dict() == {"member": {"a": 1}}
    LongOptionalUnion.from_dict({"member": {"a": 1}}) == x
