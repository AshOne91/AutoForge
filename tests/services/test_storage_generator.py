from pathlib import PurePosixPath

import yaml

from autoforge.core.specification import (
    ApplicationSpec,
    ProjectInfo,
    ProjectSpec,
    StorageSpec,
    ToolingSpec,
)
from autoforge.services.generation.storage import ObjectStorageGenerator


def specification(*, enabled: bool = True) -> ProjectSpec:
    return ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="KIS Auto Trading",
            package_name="kis_auto_trading",
            version="0.1.0",
        ),
        application=ApplicationSpec(),
        tooling=ToolingSpec(storage=StorageSpec(enabled=enabled)),
    )


def test_object_storage_generator_renders_minio_by_default() -> None:
    files = ObjectStorageGenerator().render(specification())

    assert PurePosixPath("deploy", "storage", "compose.storage.yaml") in files


def test_object_storage_generator_can_be_explicitly_disabled() -> None:
    assert ObjectStorageGenerator().render(specification(enabled=False)) == {}


def test_object_storage_generator_renders_default_minio_contract() -> None:
    files = ObjectStorageGenerator().render(specification())

    compose = files[PurePosixPath("deploy", "storage", "compose.storage.yaml")]
    environment = files[PurePosixPath("deploy", "storage", ".env.example")]
    readme = files[PurePosixPath("deploy", "storage", "README.md")]

    assert "minio/minio:RELEASE.2025-07-23T15-54-02Z" in compose
    assert "minio/mc:RELEASE.2025-08-13T08-35-41Z" in compose
    assert 'command: server /data --console-address ":9001"' in compose
    assert '"${LOCAL_BIND_ADDRESS:-127.0.0.1}:${MINIO_API_PORT:-49580}:9000"' in compose
    assert "S3_ENDPOINT_URL=http://minio:9000" in environment
    assert "S3_ACCESS_KEY=autoforge" in environment
    assert "S3_BUCKET=kis-auto-trading-artifacts" in environment
    assert "mc mb --ignore-existing" in compose
    assert "idempotently creates `S3_BUCKET`" in readme
    assert "rather than adding it to a Compose `--wait` health gate" in readme
    parsed = yaml.safe_load(compose)
    assert set(parsed["services"]) == {"minio", "minio-init"}
    assert parsed["services"]["minio"]["profiles"] == ["storage"]
    assert parsed["services"]["minio-init"]["depends_on"]["minio"]["condition"] == "service_healthy"


def test_object_storage_generator_plan_marks_all_outputs_generated() -> None:
    plan = ObjectStorageGenerator().plan(specification())

    assert len(plan.files) == 3
    assert {file.ownership.value for file in plan.files} == {"generated"}
    assert {file.source for file in plan.files} == {"project:object_storage"}
