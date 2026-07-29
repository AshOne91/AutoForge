from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, model_validator

from autoforge.core.specification.naming import validate_class_name


class FieldTypeKind(StrEnum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    UUID = "uuid"
    MODEL = "model"
    LIST = "list"
    OPTIONAL = "optional"


class FieldType(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: FieldTypeKind
    reference: str | None = None
    item: FieldType | None = None

    @model_validator(mode="after")
    def validate_structure(self) -> FieldType:
        if self.kind is FieldTypeKind.MODEL:
            if self.reference is None:
                raise ValueError("Model Type에는 reference가 필요합니다.")
            validate_class_name(self.reference)
            if self.item is not None:
                raise ValueError("Model Type에는 item을 지정할 수 없습니다.")
            return self

        if self.kind in {FieldTypeKind.LIST, FieldTypeKind.OPTIONAL}:
            if self.item is None:
                raise ValueError(f"{self.kind.value} Type에는 item이 필요합니다.")
            if self.reference is not None:
                raise ValueError(
                    f"{self.kind.value} Type에는 reference를 지정할 수 없습니다."
                )
            return self

        if self.reference is not None or self.item is not None:
            raise ValueError(
                f"{self.kind.value} Type에는 reference 또는 item을 지정할 수 없습니다."
            )
        return self
