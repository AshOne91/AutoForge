from typing import ClassVar

from autoforge.core.specification import FieldType, FieldTypeKind


class PydanticTypeRenderer:
    """공통 FieldType을 Python 3.12 타입 표현으로 변환한다."""

    _SCALAR_TYPES: ClassVar[dict[FieldTypeKind, str]] = {
        FieldTypeKind.STRING: "str",
        FieldTypeKind.INTEGER: "int",
        FieldTypeKind.NUMBER: "float",
        FieldTypeKind.BOOLEAN: "bool",
        FieldTypeKind.DATETIME: "datetime",
        FieldTypeKind.UUID: "UUID",
    }

    def render(self, field_type: FieldType) -> str:
        if field_type.kind in self._SCALAR_TYPES:
            return self._SCALAR_TYPES[field_type.kind]
        if field_type.kind is FieldTypeKind.MODEL:
            if field_type.reference is None:
                raise ValueError("Model Type에는 reference가 필요합니다.")
            return field_type.reference
        if field_type.item is None:
            raise ValueError(f"{field_type.kind.value} Type에는 item이 필요합니다.")

        item_type = self.render(field_type.item)
        if field_type.kind is FieldTypeKind.LIST:
            return f"list[{item_type}]"
        if field_type.kind is FieldTypeKind.OPTIONAL:
            return f"{item_type} | None"
        raise ValueError(f"지원하지 않는 Field Type입니다: {field_type.kind.value}")

    def imports_for(self, field_types: list[FieldType]) -> tuple[str, ...]:
        kinds = {
            nested_type.kind
            for field_type in field_types
            for nested_type in self._walk(field_type)
        }
        imports: list[str] = []
        if FieldTypeKind.DATETIME in kinds:
            imports.append("from datetime import datetime")
        if FieldTypeKind.UUID in kinds:
            imports.append("from uuid import UUID")
        return tuple(imports)

    def model_references(self, field_types: list[FieldType]) -> tuple[str, ...]:
        references = {
            nested_type.reference
            for field_type in field_types
            for nested_type in self._walk(field_type)
            if nested_type.kind is FieldTypeKind.MODEL
            and nested_type.reference is not None
        }
        return tuple(sorted(references))

    def _walk(self, field_type: FieldType) -> tuple[FieldType, ...]:
        if field_type.item is None:
            return (field_type,)
        return field_type, *self._walk(field_type.item)
