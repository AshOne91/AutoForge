import json
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
from autoforge.core.specification import DurableJobSpec, ProjectSpec

DURABLE_JOB_GENERATOR_ID: Final = "autoforge.generator.service.durable_jobs"
DURABLE_JOB_GENERATOR_VERSION: Final = "0.1.0"


class DurableJobGenerator:
    """Generate the persistent job and transactional outbox contract."""

    @property
    def generator_id(self) -> str:
        return DURABLE_JOB_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return DURABLE_JOB_GENERATOR_VERSION

    def render(self, specification: ProjectSpec) -> dict[PurePosixPath, str]:
        jobs = specification.application.durable_jobs
        if not jobs:
            return {}
        package = specification.project.package_name
        root = PurePosixPath("src", package, "infrastructure", "durable_jobs")
        files = {
            root / "__init__.py": self._render_init(),
            root / "contracts.py": self._render_contracts(jobs),
            root / "models.py": self._render_models(package),
            root / "repository.py": self._render_repository(package),
        }
        for store in sorted({job.store for job in jobs}):
            files[
                PurePosixPath("migrations", store, "versions", "0003_durable_jobs.py")
            ] = self._render_revision(store)
        return files

    def plan(self, specification: ProjectSpec) -> GenerationPlan:
        rendered = self.render(specification)
        spec_hash = specification_hash(specification)
        return GenerationPlan(
            specification_version=specification.spec_version,
            specification_hash=spec_hash,
            files=[
                PlannedFile(
                    relative_path=path,
                    generator_id=self.generator_id,
                    generator_version=self.generator_version,
                    ownership=(
                        FileOwnership.SCAFFOLDED
                        if path.parts[0] == "migrations"
                        else FileOwnership.GENERATED
                    ),
                    action=PlannedAction.CREATE,
                    specification_hash=spec_hash,
                    expected_content_hash=content_hash(content),
                    source="project:durable-jobs",
                )
                for path, content in sorted(rendered.items(), key=lambda item: item[0].as_posix())
            ],
        )

    @staticmethod
    def _render_init() -> str:
        return (
            "from .contracts import DurableJobDefinition, DurableJobStatus, JOB_DEFINITIONS\n"
            "from .repository import DurableJobRepository, DurableJobRequestResult\n"
            "\n"
            "__all__ = [\n"
            "    'DurableJobDefinition',\n"
            "    'DurableJobRepository',\n"
            "    'DurableJobRequestResult',\n"
            "    'DurableJobStatus',\n"
            "    'JOB_DEFINITIONS',\n"
            "]\n"
        )

    @staticmethod
    def _render_contracts(jobs: list[DurableJobSpec]) -> str:
        definitions = ",\n".join(
            "    "
            + json.dumps(job.name)
            + ": DurableJobDefinition(\n"
            + f"        name={json.dumps(job.name)},\n"
            + f"        store={json.dumps(job.store)},\n"
            + f"        event_type={json.dumps(job.event_type)},\n"
            + f"        routing_key={json.dumps(job.routing_key)},\n"
            + "    )"
            for job in jobs
        )
        return (
            "from dataclasses import dataclass\n"
            "from enum import StrEnum\n"
            "\n"
            "\n"
            "class DurableJobStatus(StrEnum):\n"
            "    REQUESTED = 'requested'\n"
            "    RUNNING = 'running'\n"
            "    SUCCEEDED = 'succeeded'\n"
            "    FAILED = 'failed'\n"
            "\n"
            "\n"
            "@dataclass(frozen=True, slots=True)\n"
            "class DurableJobDefinition:\n"
            "    name: str\n"
            "    store: str\n"
            "    event_type: str\n"
            "    routing_key: str\n"
            "\n"
            "\n"
            "JOB_DEFINITIONS: dict[str, DurableJobDefinition] = {\n"
            f"{definitions}\n"
            "}\n"
        )

    @staticmethod
    def _render_models(package: str) -> str:
        return (
            "from datetime import datetime\n"
            "\n"
            "from sqlalchemy import DateTime, String, Text, UniqueConstraint\n"
            "from sqlalchemy.dialects.postgresql import JSONB, UUID\n"
            "from sqlalchemy.orm import Mapped, mapped_column\n"
            "\n"
            f"from {package}.infrastructure.database.base import Base\n"
            "\n"
            "\n"
            "class DurableJobRecord(Base):\n"
            "    __tablename__ = 'durable_jobs'\n"
            "    __table_args__ = (\n"
            "        UniqueConstraint('job_type', 'run_key', name='uq_durable_jobs_type_run_key'),\n"
            "    )\n"
            "\n"
            "    job_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)\n"
            "    job_type: Mapped[str] = mapped_column(String(100), nullable=False)\n"
            "    run_key: Mapped[str] = mapped_column(String(200), nullable=False)\n"
            "    status: Mapped[str] = mapped_column(String(20), nullable=False)\n"
            "    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)\n"
            "    result: Mapped[dict[str, object] | None] = mapped_column(JSONB)\n"
            "    error: Mapped[str | None] = mapped_column(Text)\n"
            "    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)\n"
            "    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)\n"
        )

    @staticmethod
    def _render_repository(package: str) -> str:
        return (
            "from dataclasses import dataclass\n"
            "from datetime import UTC, datetime\n"
            "from uuid import uuid4\n"
            "\n"
            "from sqlalchemy import select, update\n"
            "from sqlalchemy.dialects.postgresql import insert\n"
            "from sqlalchemy.ext.asyncio import AsyncSession\n"
            "\n"
            "from .contracts import DurableJobStatus, JOB_DEFINITIONS\n"
            "from .models import DurableJobRecord\n"
            f"from {package}.infrastructure.messaging.protocol import EventMessage\n"
            f"from {package}.infrastructure.outbox.repository import OutboxWriter\n"
            "\n"
            "\n"
            "@dataclass(frozen=True, slots=True)\n"
            "class DurableJobRequestResult:\n"
            "    job_id: str\n"
            "    created: bool\n"
            "\n"
            "\n"
            "class DurableJobRepository:\n"
            "    def __init__(self, session: AsyncSession) -> None:\n"
            "        self._session = session\n"
            "\n"
            "    async def request(\n"
            "        self, *, job_type: str, run_key: str, payload: dict[str, object]\n"
            "    ) -> DurableJobRequestResult:\n"
            "        definition = JOB_DEFINITIONS[job_type]\n"
            "        now = datetime.now(UTC)\n"
            "        job_id = str(uuid4())\n"
            "        created_job_id = (\n"
            "            await self._session.execute(\n"
            "                insert(DurableJobRecord)\n"
            "                .values(\n"
            "                    job_id=job_id,\n"
            "                    job_type=definition.name,\n"
            "                    run_key=run_key,\n"
            "                    status=DurableJobStatus.REQUESTED.value,\n"
            "                    payload=payload,\n"
            "                    requested_at=now,\n"
            "                    updated_at=now,\n"
            "                )\n"
            "                .on_conflict_do_nothing(index_elements=['job_type', 'run_key'])\n"
            "                .returning(DurableJobRecord.job_id)\n"
            "            )\n"
            "        ).scalar_one_or_none()\n"
            "        if created_job_id is not None:\n"
            "            OutboxWriter(self._session).add(\n"
            "                EventMessage(\n"
            "                    event_type=definition.event_type,\n"
            "                    aggregate_id=created_job_id,\n"
            "                    payload={\n"
            "                        'job_id': created_job_id,\n"
            "                        'job_type': definition.name,\n"
            "                        'run_key': run_key,\n"
            "                        'payload': payload,\n"
            "                    },\n"
            "                    routing_key=definition.routing_key,\n"
            "                )\n"
            "            )\n"
            "            return DurableJobRequestResult(job_id=created_job_id, created=True)\n"
            "\n"
            "        existing = (\n"
            "            await self._session.execute(\n"
            "                select(DurableJobRecord.job_id).where(\n"
            "                    DurableJobRecord.job_type == definition.name,\n"
            "                    DurableJobRecord.run_key == run_key,\n"
            "                )\n"
            "            )\n"
            "        ).scalar_one()\n"
            "        return DurableJobRequestResult(job_id=existing, created=False)\n"
            "\n"
            "    async def get(self, job_id: str) -> DurableJobRecord | None:\n"
            "        return await self._session.get(DurableJobRecord, job_id)\n"
            "\n"
            "    async def transition(\n"
            "        self,\n"
            "        *,\n"
            "        job_id: str,\n"
            "        expected_status: DurableJobStatus,\n"
            "        status: DurableJobStatus,\n"
            "        result: dict[str, object] | None = None,\n"
            "        error: str | None = None,\n"
            "    ) -> bool:\n"
            "        updated = await self._session.execute(\n"
            "            update(DurableJobRecord)\n"
            "            .where(\n"
            "                DurableJobRecord.job_id == job_id,\n"
            "                DurableJobRecord.status == expected_status.value,\n"
            "            )\n"
            "            .values(\n"
            "                status=status.value,\n"
            "                result=result,\n"
            "                error=error,\n"
            "                updated_at=datetime.now(UTC),\n"
            "            )\n"
            "            .returning(DurableJobRecord.job_id)\n"
            "        )\n"
            "        return updated.scalar_one_or_none() is not None\n"
        )

    @staticmethod
    def _render_revision(store: str) -> str:
        revision = f"af_{store}_durable_jobs_0001"
        down_revision = f"af_{store}_outbox_0001"
        return (
            f'"""AutoForge durable jobs for {store}."""\n'
            "\n"
            "from alembic import op\n"
            "import sqlalchemy as sa\n"
            "from sqlalchemy.dialects import postgresql\n"
            "\n"
            f"revision = {revision!r}\n"
            f"down_revision = {down_revision!r}\n"
            f"branch_labels = {(store + '_durable_jobs',)!r}\n"
            "depends_on = None\n"
            "\n"
            "\n"
            "def upgrade() -> None:\n"
            "    op.create_table(\n"
            "        'durable_jobs',\n"
            "        sa.Column('job_id', postgresql.UUID(as_uuid=False), primary_key=True),\n"
            "        sa.Column('job_type', sa.String(length=100), nullable=False),\n"
            "        sa.Column('run_key', sa.String(length=200), nullable=False),\n"
            "        sa.Column('status', sa.String(length=20), nullable=False),\n"
            "        sa.Column('payload', postgresql.JSONB(), nullable=False),\n"
            "        sa.Column('result', postgresql.JSONB(), nullable=True),\n"
            "        sa.Column('error', sa.Text(), nullable=True),\n"
            "        sa.Column('requested_at', sa.DateTime(timezone=True), nullable=False),\n"
            "        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),\n"
            "        sa.UniqueConstraint('job_type', 'run_key', name='uq_durable_jobs_type_run_key'),\n"
            "    )\n"
            "\n"
            "\n"
            "def downgrade() -> None:\n"
            "    op.drop_table('durable_jobs')\n"
        )
