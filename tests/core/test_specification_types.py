import pytest
from pydantic import ValidationError

from autoforge.core.specification import FieldType, FieldTypeKind


def test_create_scalar_model_list_and_optional_types() -> None:
    scalar = FieldType(kind=FieldTypeKind.STRING)
    model = FieldType(kind=FieldTypeKind.MODEL, reference="ItemInfo")
    items = FieldType(kind=FieldTypeKind.LIST, item=model)
    optional_items = FieldType(kind=FieldTypeKind.OPTIONAL, item=items)

    assert scalar.kind is FieldTypeKind.STRING
    assert model.reference == "ItemInfo"
    assert items.item is model
    assert optional_items.item is items


@pytest.mark.parametrize("kind", [FieldTypeKind.MODEL])
def test_model_type_requires_reference(kind: FieldTypeKind) -> None:
    with pytest.raises(ValidationError, match="reference"):
        FieldType(kind=kind)


@pytest.mark.parametrize(
    "kind",
    [FieldTypeKind.LIST, FieldTypeKind.OPTIONAL],
)
def test_container_type_requires_item(kind: FieldTypeKind) -> None:
    with pytest.raises(ValidationError, match="item"):
        FieldType(kind=kind)


def test_scalar_type_rejects_reference_and_item() -> None:
    with pytest.raises(ValidationError, match="reference 또는 item"):
        FieldType(kind=FieldTypeKind.STRING, reference="ItemInfo")
