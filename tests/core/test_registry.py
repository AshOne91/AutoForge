from autoforge.core.registry.registry import Registry


registry = Registry()

registry.register("hello", 100)

print(registry.get("hello"))

print(registry.exists("hello"))

print(registry.names())

registry.unregister("hello")

print(registry.exists("hello"))