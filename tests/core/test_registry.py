import pytest

from autoforge.core.registry.registry import Registry


def test_register_and_get_item() -> None:
    registry = Registry[int]()

    registry.register("hello", 100)

    assert registry.get("hello") == 100
    assert registry.exists("hello")
    assert registry.names() == ["hello"]


def test_unregister_item() -> None:
    registry = Registry[int]()
    registry.register("hello", 100)

    registry.unregister("hello")

    assert not registry.exists("hello")


def test_register_duplicate_name_raises_value_error() -> None:
    registry = Registry[int]()
    registry.register("hello", 100)

    with pytest.raises(ValueError, match="'hello' is already registered"):
        registry.register("hello", 200)

    assert registry.get("hello") == 100


def test_get_missing_name_raises_key_error() -> None:
    registry = Registry[int]()

    with pytest.raises(KeyError, match="missing"):
        registry.get("missing")


def test_collection_operations() -> None:
    registry = Registry[int]()
    registry.register("second", 200)
    registry.register("first", 100)

    assert len(registry) == 2
    assert "first" in registry
    assert registry.names() == ["first", "second"]
    assert registry.values() == [200, 100]
    assert list(registry) == [200, 100]

    registry.clear()

    assert len(registry) == 0
    assert registry.names() == []
