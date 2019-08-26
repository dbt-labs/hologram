from typing import Any, Optional, Tuple, Iterable, TypeVar, Type

# we need this to denote that create_from applies to subclasses
T = TypeVar('T', bound=ValidationError)


class ValidationError(Exception):
    def __init__(
        self,
        message: str,
        validator: Any = ...,
        path: Tuple[str] = ...,
        cause: Optional[Any] = ...,
        context: Tuple[Any] = ...,
        validator_value: Any = ...,
        instance: Any = ...,
        schema: Any = ...,
        schema_path: Tuple[Any] = ...,
        parent: Any = ...,
    ) -> None: ...

    @classmethod
    def create_from(cls: Type[T], ValidationError) -> T: ...


def best_match(errors: Iterable[ValidationError]) -> ValidationError: ...
