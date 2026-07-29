from collections.abc import Iterator


class Registry[T]:
    def __init__(self) -> None:
        self._items: dict[str, T] = {}

    def register(self, name: str, item: T) -> None:

        if name in self._items:
            raise ValueError(f"'{name}' is already registered.")

        self._items[name] = item

    def unregister(self, name: str) -> None:

        self._items.pop(name, None)

    def get(self, name: str) -> T:

        if name not in self._items:
            raise KeyError(name)

        return self._items[name]

    def exists(self, name: str) -> bool:

        return name in self._items

    def names(self) -> list[str]:

        return sorted(self._items.keys())

    def values(self) -> list[T]:

        return list(self._items.values())

    def clear(self) -> None:

        self._items.clear()

    def __len__(self) -> int:

        return len(self._items)

    def __contains__(self, name: str) -> bool:

        return name in self._items

    def __iter__(self) -> Iterator[T]:

        return iter(self._items.values())
