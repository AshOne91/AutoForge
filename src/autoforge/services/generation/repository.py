from pathlib import PurePosixPath
from typing import Final

from autoforge.core.generation import (
    FileOwnership,
    GenerationPlan,
    PlannedAction,
    PlannedFile,
    content_hash,
    specification_hash,
)
from autoforge.core.specification import (
    ColumnSpec,
    ModuleSpec,
    RepositorySpec,
    TableSpec,
)
from autoforge.core.specification.naming import validate_python_name
from autoforge.services.generation.pydantic_types import PydanticTypeRenderer

REPOSITORY_GENERATOR_ID: Final = "autoforge.generator.repository"
REPOSITORY_GENERATOR_VERSION: Final = "0.1.0"
SUPPORTED_OPERATIONS: Final = frozenset({"find_by_id", "save"})


class RepositoryGenerator:
    """기술 중립 Repository Protocol과 테스트용 Fake를 생성한다."""

    def __init__(
        self,
        package_name: str,
        type_renderer: PydanticTypeRenderer | None = None,
    ) -> None:
        self._package_name = validate_python_name(package_name)
        self._type_renderer = type_renderer or PydanticTypeRenderer()

    @property
    def generator_id(self) -> str:
        return REPOSITORY_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return REPOSITORY_GENERATOR_VERSION

    def render(self, specification: ModuleSpec) -> dict[PurePosixPath, str]:
        if specification.database is None or not specification.database.repositories:
            return {}

        repositories = specification.database.repositories
        tables = {table.name: table for table in specification.database.tables}
        primary_keys = {
            repository.name: self._single_primary_key(
                repository,
                tables[repository.table],
            )
            for repository in repositories
        }
        self._validate_operations(repositories)

        generated_root = PurePosixPath(
            "src",
            self._package_name,
            "modules",
            specification.module.name,
            "generated",
        )
        return {
            generated_root / "repository.py": self._render_protocols(
                specification,
                primary_keys,
            ),
            generated_root / "fake_repository.py": self._render_fakes(
                specification,
                primary_keys,
            ),
        }

    def plan(self, specification: ModuleSpec) -> GenerationPlan:
        rendered_files = self.render(specification)
        spec_hash = specification_hash(specification)
        files = [
            PlannedFile(
                relative_path=relative_path,
                generator_id=self.generator_id,
                generator_version=self.generator_version,
                ownership=FileOwnership.GENERATED,
                action=PlannedAction.CREATE,
                specification_hash=spec_hash,
                expected_content_hash=content_hash(content),
                source=f"module:{specification.module.name}:repository",
            )
            for relative_path, content in sorted(
                rendered_files.items(),
                key=lambda item: item[0].as_posix(),
            )
        ]
        return GenerationPlan(
            specification_version=specification.spec_version,
            specification_hash=spec_hash,
            files=files,
        )

    @staticmethod
    def _single_primary_key(
        repository: RepositorySpec,
        table: TableSpec,
    ) -> ColumnSpec:
        primary_keys = [column for column in table.columns if column.primary_key]
        if len(primary_keys) != 1:
            raise ValueError(
                f"Repository '{repository.name}' Generator는 단일 Primary Key "
                "Table만 지원합니다."
            )
        return primary_keys[0]

    @staticmethod
    def _validate_operations(repositories: list[RepositorySpec]) -> None:
        for repository in repositories:
            unsupported = set(repository.operations) - SUPPORTED_OPERATIONS
            if unsupported:
                names = ", ".join(sorted(unsupported))
                raise ValueError(
                    f"Repository '{repository.name}'의 지원하지 않는 Operation: "
                    f"{names}"
                )

    def _render_protocols(
        self,
        specification: ModuleSpec,
        primary_keys: dict[str, ColumnSpec],
    ) -> str:
        assert specification.database is not None
        repositories = specification.database.repositories
        imports = ["from typing import Protocol"]
        imports.extend(
            self._type_renderer.imports_for(
                [primary_keys[repository.name].type for repository in repositories]
            )
        )
        imports.append("")
        imports.append(self._model_import(specification, repositories))
        classes = [
            self._render_protocol(repository, primary_keys[repository.name])
            for repository in repositories
        ]
        return "\n".join(imports) + "\n\n\n" + "\n\n\n".join(classes) + "\n"

    def _render_protocol(
        self,
        repository: RepositorySpec,
        primary_key: ColumnSpec,
    ) -> str:
        lines = [f"class {repository.name}(Protocol):"]
        for operation in repository.operations:
            if operation == "find_by_id":
                key_type = self._type_renderer.render(primary_key.type)
                lines.extend(
                    [
                        "    async def find_by_id(",
                        f"        self, {primary_key.name}: {key_type},",
                        f"    ) -> {repository.aggregate} | None: ...",
                    ]
                )
            elif operation == "save":
                lines.extend(
                    [
                        "    async def save(",
                        f"        self, aggregate: {repository.aggregate},",
                        "    ) -> None: ...",
                    ]
                )
        return "\n".join(lines)

    def _render_fakes(
        self,
        specification: ModuleSpec,
        primary_keys: dict[str, ColumnSpec],
    ) -> str:
        assert specification.database is not None
        repositories = specification.database.repositories
        imports = list(
            self._type_renderer.imports_for(
                [
                    primary_keys[repository.name].type
                    for repository in repositories
                ]
            )
        )
        imports.append(self._model_import(specification, repositories))
        classes = [
            self._render_fake(repository, primary_keys[repository.name])
            for repository in repositories
        ]
        return "\n".join(imports) + "\n\n\n" + "\n\n\n".join(classes) + "\n"

    def _render_fake(
        self,
        repository: RepositorySpec,
        primary_key: ColumnSpec,
    ) -> str:
        key_type = self._type_renderer.render(primary_key.type)
        lines = [
            f"class Fake{repository.name}:",
            "    def __init__(self) -> None:",
            f"        self._items: dict[{key_type}, {repository.aggregate}] = {{}}",
        ]
        for operation in repository.operations:
            if operation == "find_by_id":
                lines.extend(
                    [
                        "",
                        "    async def find_by_id(",
                        f"        self, {primary_key.name}: {key_type},",
                        f"    ) -> {repository.aggregate} | None:",
                        f"        return self._items.get({primary_key.name})",
                    ]
                )
            elif operation == "save":
                lines.extend(
                    [
                        "",
                        "    async def save(",
                        f"        self, aggregate: {repository.aggregate},",
                        "    ) -> None:",
                        f"        self._items[aggregate.{primary_key.name}] = aggregate",
                    ]
                )
        return "\n".join(lines)

    def _model_import(
        self,
        specification: ModuleSpec,
        repositories: list[RepositorySpec],
    ) -> str:
        aggregates = ", ".join(
            sorted({repository.aggregate for repository in repositories})
        )
        return (
            f"from {self._package_name}.modules.{specification.module.name}."
            f"generated.models import {aggregates}"
        )
