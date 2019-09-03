import functools
from typing import (
    Optional,
    Type,
    Union,
    Any,
    Dict,
    cast,
    Tuple,
    List,
    TypeVar,
    get_type_hints,
    Callable,
    Generic,
)
import re
from datetime import datetime
from dataclasses import fields, is_dataclass, Field, MISSING, dataclass, asdict
from uuid import UUID
from enum import Enum
import warnings

from dateutil.parser import parse
import jsonschema

JSON_ENCODABLE_TYPES = {
    str: {"type": "string"},
    int: {"type": "integer"},
    bool: {"type": "boolean"},
    float: {"type": "number"},
    type(None): {"type": "null"},
}

JsonEncodable = Union[int, float, str, bool, None]
JsonDict = Dict[str, Any]


class ValidationError(jsonschema.ValidationError):
    pass


def is_enum(field_type: Any) -> bool:
    return issubclass_safe(field_type, Enum)


def issubclass_safe(klass: Any, base: Type) -> bool:
    try:
        return issubclass(klass, base)
    except TypeError:
        return False


def is_optional(field: Any) -> bool:
    if str(field).startswith("typing.Union"):
        for arg in field.__args__:
            if isinstance(arg, type) and issubclass(arg, type(None)):
                return True

    return False


TV = TypeVar("TV")


class FieldEncoder(Generic[TV]):
    """Base class for encoding fields to and from JSON encodable values"""

    def to_wire(self, value: TV) -> JsonEncodable:
        return value  # type: ignore

    def to_python(self, value: JsonEncodable) -> TV:
        return value  # type: ignore

    @property
    def json_schema(self) -> JsonDict:
        raise NotImplementedError()


class DateTimeFieldEncoder(FieldEncoder[datetime]):
    """Encodes datetimes to RFC3339 format"""

    def to_wire(self, value: datetime) -> str:
        out = value.isoformat()

        # Assume UTC if timezone is missing
        if value.tzinfo is None:
            return out + "Z"
        return out

    def to_python(self, value: JsonEncodable) -> datetime:
        return (
            value if isinstance(value, datetime) else parse(cast(str, value))
        )

    @property
    def json_schema(self) -> JsonDict:
        return {"type": "string", "format": "date-time"}


class UuidField(FieldEncoder[UUID]):
    def to_wire(self, value: UUID) -> str:
        return str(value)

    def to_python(self, value) -> UUID:
        return UUID(value)

    @property
    def json_schema(self) -> JsonDict:
        # 'format': 'uuid' is not valid in "real" JSONSchema
        return {
            "type": "string",
            "pattern": (
                "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
            ),
        }


_ValueEncoder = Callable[[Any, Any, bool], Any]
_ValueDecoder = Callable[[str, Any, Any], Any]

T = TypeVar("T", bound="JsonSchemaMixin")


@functools.lru_cache()
def _to_camel_case(value: str) -> str:
    if "_" in value:
        parts = value.split("_")
        return "".join(
            [parts[0]] + [part[0].upper() + part[1:] for part in parts[1:]]
        )
    else:
        return value


@dataclass
class FieldMeta:
    default: Any = None
    description: Optional[str] = None

    @property
    def as_dict(self) -> Dict:
        return {
            _to_camel_case(k): v
            for k, v in asdict(self).items()
            if v is not None
        }


@functools.lru_cache()
def _validate_schema(schema_cls: Type[T]) -> JsonDict:
    schema = schema_cls.json_schema()
    jsonschema.Draft7Validator.check_schema(schema)
    return schema


# a restriction is a list of Field, str pairs
Restriction = List[Tuple[Field, str]]
# a restricted variant is a pair of an object that has fields with restrictions
# and those restrictions. Only JsonSchemaMixin subclasses may have restrictied
# fields.
RestrictedVariant = Tuple[Type[T], Restriction]


def _get_restrictions(variant_type: Type) -> Restriction:
    """Return a list of all restrictions on the given variant of a union, in
    the form of a Field, name pair, where `name` is the field's name in json
    and the Field is the dataclass-level field name.

    If the variant isn't a JsonSchemaMixin subclass, there are no restrictions.
    """
    if not issubclass_safe(variant_type, JsonSchemaMixin):
        return []
    restrictions: Restriction = []
    for field, target_name in variant_type._get_fields():
        if field.metadata and "restrict" in field.metadata:
            restrictions.append((field, target_name))
    return restrictions


def get_union_fields(
    field_type: Union[Any]
) -> Tuple[List[RestrictedVariant], List[Any]]:
    """
    Unions have a __args__ that is all their variants (after typing's
    type-collapsing magic has run, so caveat emptor...)

    JsonSchemaMixin dataclasses have `Field`s, returned by the `_get_fields`
    method.

    This method returns a tuple of two lists for any given union:
         - the first is all of the variant types that have no restrictions,
           which includes any primitives and any unrestricted fields
         - the second is all of the variant types that have restrictions, and
           their restrictions
    """
    unrestricted: List[Any] = []
    restricted: List[RestrictedVariant] = []
    for variant in field_type.__args__:
        restrictions = _get_restrictions(variant)
        if restrictions:
            restricted.append((variant, restrictions))
        else:
            unrestricted.append(variant)
    return restricted, unrestricted


def _encode_restrictions_met(
    value: Any, restrict_fields: List[Tuple[Field, str]]
) -> bool:
    return all(
        (
            hasattr(value, f.name)
            and getattr(value, f.name) in f.metadata["restrict"]
        )
        for f, _ in restrict_fields
    )


def _decode_restrictions_met(
    value: Any, restrict_fields: List[Tuple[Field, str]]
) -> bool:
    return all(
        n in value and value[n] in f.metadata["restrict"]
        for f, n in restrict_fields
    )


class JsonSchemaMixin:
    """Mixin which adds methods to generate a JSON schema and
    convert to and from JSON encodable dicts with validation against the schema
    """

    _field_encoders: Dict[Type, FieldEncoder] = {
        datetime: DateTimeFieldEncoder(),
        UUID: UuidField(),
    }

    # Cache of the generated schema
    _schema: Optional[Dict[str, JsonDict]] = None
    _definitions: Optional[Dict[str, JsonDict]] = None

    # Cache of field encode / decode functions
    _encode_cache: Optional[Dict[Any, _ValueEncoder]] = None
    _decode_cache: Optional[Dict[Any, _ValueDecoder]] = None
    _mapped_fields: Optional[List[Tuple[Field, str]]] = None

    @classmethod
    def field_mapping(cls) -> Dict[str, str]:
        """Defines the mapping of python field names to JSON field names.

        The main use-case is to allow JSON field names which are Python keywords
        """
        return {}

    @classmethod
    def register_field_encoders(cls, field_encoders: Dict[Type, FieldEncoder]):
        """Registers additional custom field encoders. If called on the base, these are added globally.

        The DateTimeFieldEncoder is included by default.
        """
        if cls is not JsonSchemaMixin:
            cls._field_encoders = {**cls._field_encoders, **field_encoders}
        else:
            cls._field_encoders.update(field_encoders)

    @classmethod
    def _encode_field(
        cls, field_type: Any, value: Any, omit_none: bool
    ) -> Any:
        if value is None:
            return value
        try:
            encoder = cls._encode_cache[field_type]  # type: ignore
        except (KeyError, TypeError):
            if cls._encode_cache is None:
                cls._encode_cache = {}

            field_type_name = cls._get_field_type_name(field_type)
            if field_type in cls._field_encoders:

                def encoder(ft, v, __):
                    return cls._field_encoders[ft].to_wire(v)

            elif is_enum(field_type):

                def encoder(_, v, __):
                    return v.value

            elif field_type_name == "Union":
                # Attempt to encode the field with each union variant.
                # TODO: Find a more reliable method than this since in the case 'Union[List[str], Dict[str, int]]' this
                # will just output the dict keys as a list
                restricted, unrestricted = get_union_fields(field_type)
                for variant, restrict_fields in restricted:
                    if _encode_restrictions_met(value, restrict_fields):
                        return cls._encode_field(variant, value, omit_none)
                encoded = None
                for variant in unrestricted:
                    try:
                        encoded = cls._encode_field(variant, value, omit_none)
                        break
                    except (TypeError, AttributeError):
                        continue
                if encoded is None:
                    raise TypeError(
                        "No variant of '{}' matched the type '{}'".format(
                            field_type, type(value)
                        )
                    )
                return encoded
            elif field_type_name in ("Mapping", "Dict"):

                def encoder(ft, val, o):
                    return {
                        cls._encode_field(
                            ft.__args__[0], k, o
                        ): cls._encode_field(ft.__args__[1], v, o)
                        for k, v in val.items()
                    }

            elif field_type_name == "PatternProperty":
                # TODO: is there some way to set __args__ on this so it can
                # just re-use Dict/Mapping?
                def encoder(ft, val, o):

                    return {
                        cls._encode_field(str, k, o): cls._encode_field(
                            ft.TARGET_TYPE, v, o
                        )
                        for k, v in val.items()
                    }

            elif field_type_name == "List" or (
                field_type_name == "Tuple" and ... in field_type.__args__
            ):

                def encoder(ft, val, o):
                    if not isinstance(val, (tuple, list)):
                        valtype = type(val)
                        # raise a TypeError so the union encoder will capture it
                        raise TypeError(
                            f"Invalid type, expected {field_type_name} but got {valtype}"
                        )
                    return [
                        cls._encode_field(ft.__args__[0], v, o) for v in val
                    ]

            elif field_type_name == "Sequence":

                def encoder(ft, val, o):
                    return [
                        cls._encode_field(ft.__args__[0], v, o) for v in val
                    ]

            elif field_type_name == "Tuple":

                def encoder(ft, val, o):
                    return [
                        cls._encode_field(ft.__args__[idx], v, o)
                        for idx, v in enumerate(val)
                    ]

            elif cls._is_json_schema_subclass(field_type):
                # Only need to validate at the top level
                def encoder(_, v, o):
                    return v.to_dict(omit_none=o, validate=False)

            elif hasattr(field_type, "__supertype__"):  # NewType field

                def encoder(ft, v, o):
                    return cls._encode_field(ft.__supertype__, v, o)

            else:

                def encoder(_, v, __):
                    return v

            cls._encode_cache[field_type] = encoder  # type: ignore
        return encoder(field_type, value, omit_none)

    @classmethod
    def _get_fields(cls) -> List[Tuple[Field, str]]:
        mapped_fields = []
        type_hints = get_type_hints(cls)

        for f in fields(cls):
            # Skip internal fields
            if f.name.startswith("_"):
                continue

            # Note fields() doesn't resolve forward refs
            f.type = type_hints[f.name]

            mapped_fields.append((f, cls.field_mapping().get(f.name, f.name)))

        return mapped_fields  # type: ignore

    def to_dict(
        self, omit_none: bool = True, validate: bool = False
    ) -> JsonDict:
        """Converts the dataclass instance to a JSON encodable dict, with optional JSON schema validation.

        If omit_none (default True) is specified, any items with value None are removed
        """
        data = {}
        for field, target_field in self._get_fields():
            value = self._encode_field(
                field.type, getattr(self, field.name), omit_none
            )
            if omit_none and value is None:
                continue
            data[target_field] = value
        if validate:
            self.validate(data)
        return data

    @classmethod
    def _decode_field(
        cls, field: str, field_type: Any, value: Any, validate: bool
    ) -> Any:
        if value is None:
            return None
        decoder = None
        try:
            decoder = cls._decode_cache[field_type]  # type: ignore
        except (KeyError, TypeError):
            if (
                type(value) in JSON_ENCODABLE_TYPES
                and field_type in JSON_ENCODABLE_TYPES
            ):
                return value
            if cls._decode_cache is None:
                cls._decode_cache = {}
            # Replace any nested dictionaries with their targets
            field_type_name = cls._get_field_type_name(field_type)

            if field_type in cls._field_encoders:

                def decoder(_, ft, val):
                    return cls._field_encoders[ft].to_python(val)

            elif cls._is_json_schema_subclass(field_type):

                def decoder(_, ft, val):
                    return ft.from_dict(val, validate=validate)

            elif field_type_name == "Union":
                # Attempt to decode the value using each decoder in turn
                union_excs = (
                    AttributeError,
                    TypeError,
                    ValueError,
                    ValidationError,
                )

                restricted, unrestricted = get_union_fields(field_type)
                for variant, restrict_fields in restricted:
                    if _decode_restrictions_met(value, restrict_fields):
                        return cls._decode_field(
                            field, variant, value, validate
                        )

                for variant in unrestricted:
                    try:
                        # we have to re-validate whatever we decode here
                        return cls._decode_field(field, variant, value, True)
                    except union_excs:
                        continue

            elif field_type_name in ("Mapping", "Dict"):

                def decoder(f, ft, val):
                    return {
                        cls._decode_field(
                            f, ft.__args__[0], k, validate
                        ): cls._decode_field(f, ft.__args__[1], v, validate)
                        for k, v in val.items()
                    }

            elif field_type_name == "List" or (
                field_type_name == "Tuple" and ... in field_type.__args__
            ):
                seq_type = tuple if field_type_name == "Tuple" else list

                def decoder(f, ft, val):
                    if not isinstance(val, (tuple, list)):
                        valtype = type(val)
                        # raise a TypeError so the Union decoder will capture it
                        raise TypeError(
                            f"Invalid type, expected {field_type_name} but got {valtype}"
                        )
                    return seq_type(
                        cls._decode_field(f, ft.__args__[0], v, validate)
                        for v in val
                    )

            # if you want to allow strings as sequences for some reason, you
            # can still use 'Sequence' to get back a list of characters...
            elif field_type_name == "Sequence":

                def decoder(f, ft, val):
                    return list(
                        cls._decode_field(f, ft.__args__[0], v, validate)
                        for v in val
                    )

            elif field_type_name == "Tuple":

                def decoder(f, ft, val):
                    return tuple(
                        cls._decode_field(f, ft.__args__[idx], v, validate)
                        for idx, v in enumerate(val)
                    )

            elif hasattr(field_type, "__supertype__"):  # NewType field

                def decoder(f, ft, val):
                    return cls._decode_field(
                        f, ft.__supertype__, val, validate
                    )

            elif is_enum(field_type):

                def decoder(_, ft, val):
                    return ft(val)

            elif field_type is Any:

                def decoder(_, __, val):
                    return val

            if decoder is None:
                raise ValidationError(
                    f"Unable to decode value for '{field}: {field_type_name}' (value={value})"
                )
                return value
            cls._decode_cache[field_type] = decoder
        return decoder(field, field_type, value)

    @classmethod
    def _find_matching_validator(cls: Type[T], data: JsonDict) -> T:
        if cls is not JsonSchemaMixin:
            raise NotImplementedError

        decoded = None

        for subclass in cls.__subclasses__():
            try:
                if is_dataclass(subclass):
                    return subclass.from_dict(data)

            except ValidationError:
                continue

        if decoded is None:
            raise ValidationError("No matching validator for data.")

        return decoded

    @classmethod
    def from_dict(cls: Type[T], data: JsonDict, validate=True) -> T:
        """Returns a dataclass instance with all nested classes converted from the dict given"""
        if cls is JsonSchemaMixin:
            return cls._find_matching_validator(data)

        init_values: Dict[str, Any] = {}
        non_init_values: Dict[str, Any] = {}

        if validate:
            cls.validate(data)

        for field, target_field in cls._get_fields():
            values = init_values if field.init else non_init_values
            if target_field in data or (
                field.default == MISSING
                and field.default_factory == MISSING  # type: ignore
            ):
                values[field.name] = cls._decode_field(
                    field.name, field.type, data.get(target_field), validate
                )

        # Need to ignore the type error here, since mypy doesn't know that
        # subclasses are dataclasses
        instance = cls(**init_values)  # type: ignore

        for field_name, value in non_init_values.items():
            setattr(instance, field_name, value)

        return instance

    @staticmethod
    def _is_json_schema_subclass(field_type: Type) -> bool:
        return issubclass_safe(field_type, JsonSchemaMixin)

    @staticmethod
    def _has_definition(field_type: Type) -> bool:
        return (
            issubclass_safe(field_type, JsonSchemaMixin)
            and field_type.__name__ != "PatternProperty"
        )

    @classmethod
    def _get_field_meta(cls, field: Field) -> Tuple[FieldMeta, bool]:
        required = True
        field_meta = FieldMeta()
        default_value: Optional[Callable[[], Any]] = None
        if field.default is not MISSING and field.default is not None:
            # In case of default value given
            default_value = field.default
        elif (
            field.default_factory is not MISSING  # type: ignore
            and field.default_factory is not None  # type: ignore
        ):  # type: ignore
            # In case of a default factory given, we call it
            default_value = field.default_factory()  # type: ignore

        if default_value is not None:
            field_meta.default = cls._encode_field(
                field.type, default_value, omit_none=False
            )
            required = False

        if field.metadata is not None:
            if "description" in field.metadata:
                field_meta.description = field.metadata["description"]

        return field_meta, required

    @classmethod
    def _encode_restrictions(
        cls, restrictions: Union[List[Any], Type[Enum]]
    ) -> JsonDict:
        field_schema: JsonDict = {}
        member_types = set()
        values = []
        for member in restrictions:
            if isinstance(member, Enum):
                value = member.value
            else:
                value = member
            member_types.add(type(value))
            values.append(value)
        if len(member_types) == 1:
            member_type = member_types.pop()
            if member_type in JSON_ENCODABLE_TYPES:
                field_schema.update(JSON_ENCODABLE_TYPES[member_type])
            else:
                field_schema.update(
                    cls._field_encoders[member_type].json_schema
                )
        else:
            # hologram used to silently do nothing here, which seems worse
            raise ValidationError(
                "Invalid schema defined: Found multiple member types - {!s}".format(
                    member_types
                )
            )
        field_schema["enum"] = values
        return field_schema

    @classmethod
    def _get_schema_for_type(
        cls,
        target: Type,
        required: bool = True,
        restrictions: Optional[List[Any]] = None,
    ) -> Tuple[JsonDict, bool]:

        field_schema: JsonDict = {"type": "object"}

        type_name = cls._get_field_type_name(target)

        if target in cls._field_encoders:
            field_schema.update(cls._field_encoders[target].json_schema)

        elif restrictions:
            field_schema.update(cls._encode_restrictions(restrictions))

        # if Union[..., None] or Optional[...]
        elif type_name == "Union":
            field_schema = {
                "oneOf": [
                    cls._get_field_schema(variant)[0]
                    for variant in target.__args__
                ]
            }

            if is_optional(target):
                required = False

        elif is_enum(target):
            field_schema.update(cls._encode_restrictions(target))

        elif type_name in ("Dict", "Mapping"):
            field_schema = {"type": "object"}
            if target.__args__[1] is not Any:
                field_schema["additionalProperties"] = cls._get_field_schema(
                    target.__args__[1]
                )[0]
        elif type_name == "PatternProperty":
            field_schema = {"type": "object"}
            field_schema["patternProperties"] = {
                ".*": cls._get_field_schema(target.TARGET_TYPE)[0]
            }

        elif type_name in ("Sequence", "List") or (
            type_name == "Tuple" and ... in target.__args__
        ):
            field_schema = {"type": "array"}
            if target.__args__[0] is not Any:
                field_schema["items"] = cls._get_field_schema(
                    target.__args__[0]
                )[0]

        elif type_name == "Tuple":
            tuple_len = len(target.__args__)
            # TODO: How do we handle Optional type within lists / tuples
            field_schema = {
                "type": "array",
                "minItems": tuple_len,
                "maxItems": tuple_len,
                "items": [
                    cls._get_field_schema(type_arg)[0]
                    for type_arg in target.__args__
                ],
            }

        elif target in JSON_ENCODABLE_TYPES:
            field_schema.update(JSON_ENCODABLE_TYPES[target])

        elif hasattr(target, "__supertype__"):  # NewType fields
            field_schema, _ = cls._get_field_schema(target.__supertype__)

        else:
            raise ValidationError(f"Unable to create schema for '{type_name}'")
        return field_schema, required

    @classmethod
    def _get_field_schema(
        cls, field: Union[Field, Type]
    ) -> Tuple[JsonDict, bool]:
        required = True
        restrictions = None

        if isinstance(field, Field):
            field_type = field.type
            field_meta, required = cls._get_field_meta(field)
            if field.metadata is not None:
                restrictions = field.metadata.get("restrict")
        else:
            field_type = field
            field_meta = FieldMeta()

        field_type_name = cls._get_field_type_name(field_type)

        if cls._has_definition(field_type):
            field_schema: JsonDict = {
                "$ref": "#/definitions/{}".format(field_type_name)
            }
        else:
            field_schema, required = cls._get_schema_for_type(
                field_type, required=required, restrictions=restrictions
            )

        field_schema.update(field_meta.as_dict)

        return field_schema, required

    @classmethod
    def _get_field_definitions(cls, field_type: Any, definitions: JsonDict):
        field_type_name = cls._get_field_type_name(field_type)
        if is_optional(field_type) or field_type_name in (
            "Sequence",
            "List",
            "Tuple",
        ):
            cls._get_field_definitions(field_type.__args__[0], definitions)
        elif field_type_name in ("Dict", "Mapping"):
            cls._get_field_definitions(field_type.__args__[1], definitions)
        elif field_type_name == "PatternProperty":
            cls._get_field_definitions(field_type.TARGET_TYPE, definitions)
        elif field_type_name == "Union":
            for variant in field_type.__args__:
                cls._get_field_definitions(variant, definitions)
        elif cls._is_json_schema_subclass(field_type):
            # Prevent recursion from forward refs & circular type dependencies
            if field_type.__name__ not in definitions:
                definitions[field_type.__name__] = None
                definitions.update(field_type.json_schema(embeddable=True))

    @classmethod
    def all_json_schemas(cls) -> JsonDict:
        """Returns JSON schemas for all subclasses"""
        definitions = {}
        for subclass in cls.__subclasses__():
            if is_dataclass(subclass):
                definitions.update(subclass.json_schema(embeddable=True))
            else:
                definitions.update(subclass.all_json_schemas())
        return definitions

    @classmethod
    def _cache_definitions(cls) -> JsonDict:
        definitions: JsonDict = {}

        if cls._definitions is None:
            cls._definitions = {cls.__name__: definitions}
        elif cls.__name__ not in cls._definitions:
            cls._definitions[cls.__name__] = definitions
        else:
            definitions = cls._definitions[cls.__name__]
        return definitions

    @classmethod
    def _cache_schema(cls, schema: JsonDict) -> None:
        if cls._schema is None:
            cls._schema = {}

        cls._schema[cls.__name__] = schema

    @classmethod
    def _collect_json_schema(cls, definitions: JsonDict) -> JsonDict:
        """Return the schema dictionary and update the definitions dictionary
        for this class.
        """
        properties = {}
        required = []
        for field, target_field in cls._get_fields():
            properties[target_field], is_required = cls._get_field_schema(
                field
            )
            cls._get_field_definitions(field.type, definitions)
            if is_required:
                required.append(target_field)

        schema = {
            "type": "object",
            "required": required,
            "properties": properties,
            "additionalProperties": False,
        }
        if cls.__doc__:
            schema["description"] = cls.__doc__
        return schema

    @classmethod
    def _schema_from_cache(cls, definitions: JsonDict) -> JsonDict:

        if cls._schema is not None and cls.__name__ in cls._schema:
            schema = cls._schema[cls.__name__]
        else:
            schema = cls._collect_json_schema(definitions)
            cls._cache_schema(schema)
        return schema

    @classmethod
    def json_schema(cls, embeddable: bool = False) -> JsonDict:
        """Returns the JSON schema for the dataclass, along with the schema of any nested dataclasses
        within the 'definitions' field.

        Enable the embeddable flag to generate the schema in a format for embedding into other schemas
        or documents supporting JSON schema such as Swagger specs.
        """
        if cls is JsonSchemaMixin:
            warnings.warn(
                "Calling 'JsonSchemaMixin.json_schema' is deprecated. Use 'JsonSchemaMixin.all_json_schemas' instead",
                DeprecationWarning,
            )
            return cls.all_json_schemas()

        definitions: JsonDict = cls._cache_definitions()
        schema: JsonDict = cls._schema_from_cache(definitions)

        if embeddable:
            return {**definitions, cls.__name__: schema}

        return {
            **schema,
            **{
                "definitions": definitions,
                "$schema": "http://json-schema.org/draft-07/schema#",
            },
        }

    @staticmethod
    def _get_field_type_name(field_type: Any) -> str:
        try:
            return field_type.__name__
        except AttributeError:
            # The types in the 'typing' module lack the __name__ attribute
            match = re.match(r"typing\.([A-Za-z]+)", str(field_type))
            return str(field_type) if match is None else match.group(1)

    @classmethod
    def validate(cls, data: Any):
        schema = _validate_schema(cls)
        validator = jsonschema.Draft7Validator(schema)
        error = jsonschema.exceptions.best_match(validator.iter_errors(data))
        if error is not None:
            raise ValidationError.create_from(error) from error
