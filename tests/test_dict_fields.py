import pytest

from dataclasses import dataclass
from hologram import JsonSchemaMixin
from typing import Dict, Union


@dataclass
class DictFieldValue(JsonSchemaMixin):
    z: str


@dataclass
class SecondDictFieldValue(JsonSchemaMixin):
    z: int


@dataclass
class HasDictFields(JsonSchemaMixin):
    a: str
    x: Dict[str, str]
    z: Dict[str, Union[DictFieldValue, SecondDictFieldValue]]


def test_schema():
    schema = HasDictFields.json_schema()

    assert schema["type"] == "object"
    assert schema["required"] == ["a", "x", "z"]
    assert schema["properties"] == {
        "a": {"type": "string"},
        "x": {"type": "object", "additionalProperties": {"type": "string"}},
        "z": {
            "type": "object",
            "additionalProperties": {
                "oneOf": [
                    {"$ref": "#/definitions/DictFieldValue"},
                    {"$ref": "#/definitions/SecondDictFieldValue"},
                ]
            },
        },
    }
