from dataclasses import dataclass
from typing import Tuple

from hologram import JsonSchemaMixin


@dataclass
class TupleMember(JsonSchemaMixin):
    a: int


@dataclass
class TupleEllipsisHolder(JsonSchemaMixin):
    member: Tuple[TupleMember, ...]


@dataclass
class TupleMemberFirstHolder(JsonSchemaMixin):
    member: Tuple[TupleMember, str]


@dataclass
class TupleMemberSecondHolder(JsonSchemaMixin):
    member: Tuple[str, TupleMember]


def test_ellipsis_tuples():
    dct = {"member": [{"a": 1}, {"a": 2}, {"a": 3}]}
    value = TupleEllipsisHolder(
        member=(TupleMember(1), TupleMember(2), TupleMember(3))
    )
    assert value.to_dict() == dct
    assert TupleEllipsisHolder.from_dict(dct) == value


def test_member_first_tuple():
    dct = {"member": [{"a": 1}, "a"]}
    value = TupleMemberFirstHolder(member=(TupleMember(1), "a"))
    TupleMemberFirstHolder.from_dict(dct) == value
    value.to_dict() == dct


def test_member_second_tuple():
    dct = {"member": ["a", {"a": 1}]}
    value = TupleMemberSecondHolder(member=("a", TupleMember(1)))
    TupleMemberSecondHolder.from_dict(dct) == value
    value.to_dict() == dct
