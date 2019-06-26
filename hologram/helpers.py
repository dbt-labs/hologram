from enum import Enum


class StrEnum(str, Enum):
    def __str__(self):
        return self.value

    # https://docs.python.org/3.6/library/enum.html#using-automatic-values
    def _generate_next_value_(name, start, count, last_values):
        return name


def StrLiteral(value: str):
    return StrEnum(value, value)
