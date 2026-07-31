import ast
import sys
from pathlib import Path, PurePosixPath
from uuid import uuid4

import pytest

from autoforge.core.generation import FileOwnership, Generator, content_hash
from autoforge.core.specification import (
    ColumnSpec,
    DatabaseSpec,
    DataPlacementSpec,
    FieldSpec,
    FieldType,
    FieldTypeKind,
    ModelSpec,
    ModuleInfo,
    ModuleSpec,
    RepositoryQuerySpec,
    RepositorySpec,
    TableSpec,
)
from autoforge.core.workspace import Workspace
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.services.generation import (
    FastAPIModuleGenerator,
    GenerationPlanApplier,
    GenerationPlanResolver,
    RepositoryGenerator,
)


def account_specification() -> ModuleSpec:
    user_id_type = FieldType(kind=FieldTypeKind.UUID)
    return ModuleSpec(
        spec_version="1",
        module=ModuleInfo(
            name="account",
            display_name="Account",
            route_prefix="/api/account",
        ),
        models=[
            ModelSpec(
                name="UserProfile",
                fields=[
                    FieldSpec(name="user_id", type=user_id_type),
                    FieldSpec(
                        name="risk_tolerance",
                        type=FieldType(kind=FieldTypeKind.STRING),
                    ),
                ],
            )
        ],
        database=DatabaseSpec(
            tables=[
                TableSpec(
                    name="user_profiles",
                    columns=[
                        ColumnSpec(
                            name="user_id",
                            type=user_id_type,
                            primary_key=True,
                        ),
                        ColumnSpec(
                            name="risk_tolerance",
                            type=FieldType(kind=FieldTypeKind.STRING),
                        ),
                    ],
                )
            ],
            repositories=[
                RepositorySpec(
                    name="UserProfileRepository",
                    aggregate="UserProfile",
                    table="user_profiles",
                    operations=["find_by_id", "save"],
                )
            ],
            placements=[
                DataPlacementSpec(
                    table="user_profiles",
                    store="identity",
                    partition_key="user_id",
                )
            ],
        ),
    )


def test_repository_generator_satisfies_protocol() -> None:
    generator: Generator[ModuleSpec] = RepositoryGenerator("kis_auto_trading")

    assert isinstance(generator, Generator)


def test_render_returns_protocol_and_fake_repository() -> None:
    files = RepositoryGenerator("kis_auto_trading").render(
        account_specification()
    )

    assert set(files) == {
        PurePosixPath(
            "src/kis_auto_trading/modules/account/generated/repository.py"
        ),
        PurePosixPath(
            "src/kis_auto_trading/modules/account/generated/fake_repository.py"
        ),
    }
    protocol = files[
        PurePosixPath(
            "src/kis_auto_trading/modules/account/generated/repository.py"
        )
    ]
    fake = files[
        PurePosixPath(
            "src/kis_auto_trading/modules/account/generated/fake_repository.py"
        )
    ]
    ast.parse(protocol)
    ast.parse(fake)
    assert "class UserProfileRepository(Protocol):" in protocol
    assert "user_id: UUID" in protocol
    assert "-> UserProfile | None" in protocol
    assert "class FakeUserProfileRepository:" in fake
    assert "self._items: dict[UUID, UserProfile]" in fake
    assert "self._items[aggregate.user_id] = aggregate" in fake


def test_plan_marks_repository_files_generated() -> None:
    generator = RepositoryGenerator("kis_auto_trading")
    specification = account_specification()
    rendered = generator.render(specification)

    plan = generator.plan(specification)

    assert len(plan.files) == 2
    assert all(
        file.ownership is FileOwnership.GENERATED for file in plan.files
    )
    for planned_file in plan.files:
        assert planned_file.expected_content_hash == content_hash(
            rendered[planned_file.relative_path]
        )


def test_spec_without_repositories_produces_empty_plan() -> None:
    specification = ModuleSpec(
        spec_version="1",
        module=ModuleInfo(
            name="account",
            display_name="Account",
            route_prefix="/api/account",
        ),
    )
    generator = RepositoryGenerator("kis_auto_trading")

    assert generator.render(specification) == {}
    assert generator.plan(specification).files == []


def test_rejects_unsupported_operation_and_composite_primary_key() -> None:
    unsupported = account_specification()
    assert unsupported.database is not None
    unsupported.database.repositories[0].operations.append("delete_all")

    with pytest.raises(ValueError, match="지원하지 않는 Operation"):
        RepositoryGenerator("kis_auto_trading").render(unsupported)

    composite = account_specification()
    assert composite.database is not None
    composite.database.tables[0].columns.append(
        ColumnSpec(
            name="tenant_id",
            type=FieldType(kind=FieldTypeKind.UUID),
            primary_key=True,
        )
    )

    with pytest.raises(ValueError, match="단일 Primary Key"):
        RepositoryGenerator("kis_auto_trading").render(composite)


def test_render_unique_query_in_protocol_and_fake() -> None:
    specification = account_specification()
    assert specification.database is not None
    table = specification.database.tables[0]
    table.columns[1].unique = True
    repository = specification.database.repositories[0]
    repository.queries.append(
        RepositoryQuerySpec(
            name="find_by_risk_tolerance",
            column="risk_tolerance",
        )
    )

    files = RepositoryGenerator("kis_auto_trading").render(specification)
    protocol = files[PurePosixPath(
        "src/kis_auto_trading/modules/account/generated/repository.py"
    )]
    fake = files[PurePosixPath(
        "src/kis_auto_trading/modules/account/generated/fake_repository.py"
    )]

    assert "async def find_by_risk_tolerance(" in protocol
    assert "risk_tolerance: str" in protocol
    assert "if item.risk_tolerance == risk_tolerance" in fake


@pytest.mark.anyio
async def test_generated_fake_repository_can_save_and_find(
    tmp_path: Path,
) -> None:
    specification = account_specification()
    workspace = Workspace(tmp_path)
    module_generator = FastAPIModuleGenerator("kis_auto_trading")
    repository_generator = RepositoryGenerator("kis_auto_trading")

    for generator in (module_generator, repository_generator):
        rendered = generator.render(specification)
        resolved = GenerationPlanResolver().resolve(
            generator.plan(specification),
            workspace,
        )
        GenerationPlanApplier().apply(
            job_id=f"{generator.generator_id}-job",
            plan=resolved,
            rendered_files=rendered,
            workspace=workspace,
        )

    user_id = uuid4()
    code = (
        "import asyncio\n"
        "import sys\n"
        "from uuid import UUID\n"
        "\n"
        "sys.path.insert(0, 'src')\n"
        "from kis_auto_trading.modules.account.generated.models "
        "import UserProfile\n"
        "from kis_auto_trading.modules.account.generated.fake_repository "
        "import FakeUserProfileRepository\n"
        "\n"
        f"user_id = UUID('{user_id}')\n"
        "repository = FakeUserProfileRepository()\n"
        "profile = UserProfile(user_id=user_id, risk_tolerance='MODERATE')\n"
        "\n"
        "\n"
        "async def verify():\n"
        "    await repository.save(profile)\n"
        "    assert await repository.find_by_id(user_id) == profile\n"
        "\n"
        "\n"
        "asyncio.run(verify())"
    )
    result = await AsyncioProcessRunner().run(
        (sys.executable, "-c", code),
        cwd=workspace.root,
        timeout_seconds=10,
    )

    assert result.succeeded, result.stderr
