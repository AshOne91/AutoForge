# Plugins

AutoForge가 기본 제공하는 Plugin 조립 계층이다.

`create_builtin_plugin_catalog()`는 FastAPI Project/Module Generator와
Project Validator Registry를 하나의 불변 Catalog로 묶는다. package name과
ProcessRunner는 호출자가 명시적으로 주입하며, Catalog를 전역 상태로
보관하지 않는다.

외부 Plugin 디렉터리를 발견하고 신뢰 경계에서 로딩하는 책임은
`core.plugin.PluginLoader`에 있으며 Built-in Catalog와 분리한다.

전체 Registry, Manager, Loader와 Metadata 계약은
[`plugin_system.md`](../../../docs/architecture/plugin_system.md)를 따른다.
