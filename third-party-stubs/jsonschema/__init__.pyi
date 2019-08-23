from typing import Any, Dict, Iterable

# we need the 'as' to tell mypy we want this visible with both names
from jsonschema.exceptions import ValidationError as ValidationError


class Draft7Validator:
    def __init__(self, schema: Dict[str, Any]) -> None: ...
    @classmethod
    def check_schema(cls, schema: Dict[str, Any]) -> None: ...
    def iter_errors(self, instance, _schema=None) -> Iterable[ValidationError]: ...
