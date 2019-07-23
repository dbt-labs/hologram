from hologram import JsonSchemaMixin

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class Foo(JsonSchemaMixin):
    x: int = 100
    y: List[str] = field(default_factory=list)
    z: Dict[str, Any] = field(default_factory=dict)


def test_basic():
    foo = Foo()
    assert foo.to_dict() == {"x": 100, "y": [], "z": {}}
    assert Foo.from_dict({}) == foo


def test_complex():
    json_obj = {
        "a": 1,
        "b": ["hello", "world!"],
        "c": {"key1": ["value1", "value2"], "key2": "just a string"},
    }
    full_dict = {"x": 10, "y": ["a", "b"], "z": json_obj}
    foo = Foo(10, ["a", "b"], json_obj)
    assert foo.to_dict() == full_dict
    assert Foo.from_dict(full_dict) == foo
