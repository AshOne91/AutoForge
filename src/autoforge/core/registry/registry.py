from typing import Generic, TypeVar


T = TypeVar("T")


class Registry(Generic[T]):
    """
    공통 Registry

    Plugin
    Task
    Pipeline
    등을 등록한다.
    """

    def __init__(self):
        self._items: dict[str, T] = {}

    def register(self, name: str, item: T):

        if name in self._items:
            raise ValueError(
                f"'{name}' is already registered."
            )

        self._items[name] = item

    def unregister(self, name: str):

        self._items.pop(name, None)

    def get(self, name: str) -> T:

        if name not in self._items:
            raise KeyError(name)

        return self._items[name]

    def exists(self, name: str) -> bool:

        return name in self._items

    def list(self) -> list[str]:

        return sorted(self._items.keys())

    def clear(self):

        self._items.clear()