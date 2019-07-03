from dataclasses import fields
from enum import Enum
from typing import Type, NewType

from . import JsonSchemaMixin, FieldEncoder, JsonDict


class StrEnum(str, Enum):
    def __str__(self):
        return self.value

    # https://docs.python.org/3.6/library/enum.html#using-automatic-values
    def _generate_next_value_(name, start, count, last_values):
        return name


def StrLiteral(value: str):
    return StrEnum(value, value)


def NewPatternType(name: str, pattern: str) -> Type:
    thing = NewType(name, str)

    class PatternEncoder(FieldEncoder):
        @property
        def json_schema(self):
            return {"type": "string", "pattern": pattern}

    JsonSchemaMixin.register_field_encoders({thing: PatternEncoder()})
    return thing


class HyphenatedJsonSchemaMixin(JsonSchemaMixin):
    @classmethod
    def field_mapping(cls):
        result = {}
        for field in fields(cls):
            skip = field.metadata.get("preserve_underscore")
            if skip:
                continue

            if "_" in field.name:
                result[field.name] = field.name.replace("_", "-")
        return result


class ExtensibleJsonSchemaMixin(JsonSchemaMixin):
    @classmethod
    def _collect_json_schema(cls, definitions: JsonDict) -> JsonDict:
        dct = super()._collect_json_schema(definitions=definitions)
        dct["additionalProperties"] = True
        return dct
