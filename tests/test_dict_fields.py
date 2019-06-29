import pytest

from dataclasses import dataclass
from hologram import JsonSchemaMixin
from typing import Dict


@dataclass
class DictFieldValue(JsonSchemaMixin):
    z: str


@dataclass
class HasDictFields(JsonSchemaMixin):
    a: str
    x: Dict[str, str]
    z: Dict[str, DictFieldValue]


def test_schema():
    schema = HasDictFields.json_schema()

    assert schema["type"] == "object"
    assert schema["required"] == ["a", "x", "z"]
    assert schema["properties"] == {
        "a": {"type": "string"},
        "x": {"type": "object", "additionalProperties": {"type": "string"}},
        "z": {
            "type": "object",
            "additionalProperties": {"$ref": "#/definitions/DictFieldValue"},
        },
    }
