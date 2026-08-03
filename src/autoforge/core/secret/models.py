from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SecretReference:
    name: str

    def __post_init__(self) -> None:
        if (
            not self.name
            or self.name != self.name.strip()
            or len(self.name) > 255
            or any(ord(character) < 32 for character in self.name)
        ):
            raise ValueError("Secret reference name is invalid")


@dataclass(frozen=True, slots=True)
class SecretValue:
    _value: str = field(repr=False)

    def __post_init__(self) -> None:
        if not self._value:
            raise ValueError("Secret value must not be empty")

    def __repr__(self) -> str:
        return "SecretValue(***)"

    def __str__(self) -> str:
        return "***"

    def reveal(self) -> str:
        return self._value
