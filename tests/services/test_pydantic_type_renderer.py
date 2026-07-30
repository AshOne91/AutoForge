from autoforge.core.specification import FieldType, FieldTypeKind
from autoforge.services.generation import PydanticTypeRenderer


def field_type(
    kind: FieldTypeKind,
    *,
    item: FieldType | None = None,
    reference: str | None = None,
) -> FieldType:
    return FieldType(kind=kind, item=item, reference=reference)


def test_render_scalar_types() -> None:
    renderer = PydanticTypeRenderer()

    assert renderer.render(field_type(FieldTypeKind.STRING)) == "str"
    assert renderer.render(field_type(FieldTypeKind.INTEGER)) == "int"
    assert renderer.render(field_type(FieldTypeKind.NUMBER)) == "float"
    assert renderer.render(field_type(FieldTypeKind.BOOLEAN)) == "bool"
    assert renderer.render(field_type(FieldTypeKind.DATETIME)) == "datetime"
    assert renderer.render(field_type(FieldTypeKind.UUID)) == "UUID"


def test_render_model_list_and_optional_types() -> None:
    renderer = PydanticTypeRenderer()
    model = field_type(FieldTypeKind.MODEL, reference="ItemInfo")
    items = field_type(FieldTypeKind.LIST, item=model)
    optional_items = field_type(FieldTypeKind.OPTIONAL, item=items)

    assert renderer.render(model) == "ItemInfo"
    assert renderer.render(items) == "list[ItemInfo]"
    assert renderer.render(optional_items) == "list[ItemInfo] | None"


def test_collect_required_imports_recursively() -> None:
    renderer = PydanticTypeRenderer()
    types = [
        field_type(FieldTypeKind.DATETIME),
        field_type(
            FieldTypeKind.LIST,
            item=field_type(FieldTypeKind.UUID),
        ),
    ]

    assert renderer.imports_for(types) == (
        "from datetime import datetime",
        "from uuid import UUID",
    )


def test_collect_sorted_model_references() -> None:
    renderer = PydanticTypeRenderer()
    types = [
        field_type(FieldTypeKind.MODEL, reference="UserInfo"),
        field_type(
            FieldTypeKind.OPTIONAL,
            item=field_type(FieldTypeKind.MODEL, reference="ItemInfo"),
        ),
    ]

    assert renderer.model_references(types) == ("ItemInfo", "UserInfo")
