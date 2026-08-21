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
from autoforge.core.specification import DurableJobSpec, ProjectSpec, ServiceSpec
from autoforge.services.generation.alembic import alembic_revision_id

DURABLE_JOB_GENERATOR_ID: Final = "autoforge.generator.service.durable_jobs"
DURABLE_JOB_GENERATOR_VERSION: Final = "0.1.1"


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
        rabbitmq_services = [
            service
            for service in specification.application.services
            if service.kind == "rabbitmq"
        ]
        if len(rabbitmq_services) != 1:
            raise ValueError("durable jobs require one RabbitMQ service")
        package = specification.project.package_name
        root = PurePosixPath("src", package, "infrastructure", "durable_jobs")
        files = {
            root / "__init__.py": self._render_init(),
            root / "contracts.py": self._render_contracts(jobs),
            root / "models.py": self._render_models(package),
            root / "repository.py": self._render_repository(package),
            root / "worker.py": self._render_worker(package),
            PurePosixPath(
                "src", package, "application", "durable_job_handler.py"
            ): self._render_handler_scaffold(package),
            PurePosixPath("scripts", "run_durable_job_worker.py"): (
                self._render_worker_runner(
                    specification,
                    rabbitmq_services[0],
                )
            ),
        }
        for store in sorted({job.store for job in jobs}):
            files[
                PurePosixPath("migrations", store, "versions", "0003_durable_jobs.py")
            ] = self._render_revision(store)
        for job in jobs:
            if job.schedule is not None:
                files[
                    PurePosixPath("airflow", "dags", f"{job.name}.py")
                ] = self._render_airflow_dag(
                    job,
                    specification.application.service_token_environments[
                        "durable_jobs"
                    ],
                )
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
                        or path.name == "durable_job_handler.py"
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
            "from .contracts import (\n"
            "    JOB_DEFINITIONS,\n"
            "    JOB_STATUS_EVENT_TYPE,\n"
            "    JOB_STATUS_ROUTING_KEY,\n"
            "    DurableJobDefinition,\n"
            "    DurableJobStatus,\n"
            ")\n"
            "from .repository import DurableJobRepository, DurableJobRequestResult\n"
            "from .worker import DurableJobExecution, DurableJobHandler, DurableJobMessageHandler\n"
            "\n"
            "__all__ = [\n"
            "    'JOB_DEFINITIONS',\n"
            "    'JOB_STATUS_EVENT_TYPE',\n"
            "    'JOB_STATUS_ROUTING_KEY',\n"
            "    'DurableJobDefinition',\n"
            "    'DurableJobExecution',\n"
            "    'DurableJobHandler',\n"
            "    'DurableJobMessageHandler',\n"
            "    'DurableJobRepository',\n"
            "    'DurableJobRequestResult',\n"
            "    'DurableJobStatus',\n"
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
            "JOB_STATUS_EVENT_TYPE = 'durable-job.status.changed'\n"
            "JOB_STATUS_ROUTING_KEY = 'durable-job.status.changed'\n"
            "\n"
            "\n"
            "class DurableJobStatus(StrEnum):\n"
            "    REQUESTED = 'requested'\n"
            "    RUNNING = 'running'\n"
            "    SUCCEEDED = 'succeeded'\n"
            "    FAILED = 'failed'\n"
            "    CANCELLED = 'cancelled'\n"
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
            f"from {package}.infrastructure.messaging.protocol import EventMessage\n"
            f"from {package}.infrastructure.outbox.repository import OutboxWriter\n"
            "\n"
            "from .contracts import (\n"
            "    JOB_DEFINITIONS,\n"
            "    JOB_STATUS_EVENT_TYPE,\n"
            "    JOB_STATUS_ROUTING_KEY,\n"
            "    DurableJobStatus,\n"
            ")\n"
            "from .models import DurableJobRecord\n"
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
            "        self,\n"
            "        *,\n"
            "        job_type: str,\n"
            "        run_key: str,\n"
            "        payload: dict[str, object],\n"
            "        available_at: datetime | None = None,\n"
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
            "                ),\n"
            "                available_at=available_at,\n"
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
            "        return await self._session.get(\n"
            "            DurableJobRecord, job_id, populate_existing=True\n"
            "        )\n"
            "\n"
            "    async def list_recent(\n"
            "        self, *, job_type: str, limit: int\n"
            "    ) -> list[DurableJobRecord]:\n"
            "        records = await self._session.execute(\n"
            "            select(DurableJobRecord)\n"
            "            .where(DurableJobRecord.job_type == job_type)\n"
            "            .order_by(\n"
            "                DurableJobRecord.updated_at.desc(), DurableJobRecord.job_id.desc()\n"
            "            )\n"
            "            .limit(limit)\n"
            "        )\n"
            "        return list(records.scalars())\n"
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
            "        transitioned = updated.scalar_one_or_none() is not None\n"
            "        if transitioned:\n"
            "            OutboxWriter(self._session).add(\n"
            "                EventMessage(\n"
            "                    event_type=JOB_STATUS_EVENT_TYPE,\n"
            "                    aggregate_id=job_id,\n"
            "                    payload={\n"
            "                        'job_id': job_id,\n"
            "                        'status': status.value,\n"
            "                        'result': result,\n"
            "                        'error': error,\n"
            "                    },\n"
            "                    routing_key=JOB_STATUS_ROUTING_KEY,\n"
            "                )\n"
            "            )\n"
            "        return transitioned\n"
        )

    @staticmethod
    def _render_worker(package: str) -> str:
        return (
            "from dataclasses import dataclass\n"
            "from typing import Protocol\n"
            "\n"
            f"from {package}.infrastructure.database.routing import ShardTarget\n"
            f"from {package}.infrastructure.database.session import AsyncSessionRegistry\n"
            f"from {package}.infrastructure.messaging.protocol import EventMessage\n"
            "\n"
            "from .contracts import JOB_DEFINITIONS, DurableJobStatus\n"
            "from .repository import DurableJobRepository\n"
            "\n"
            "\n"
            "@dataclass(frozen=True, slots=True)\n"
            "class DurableJobExecution:\n"
            "    job_id: str\n"
            "    job_type: str\n"
            "    run_key: str\n"
            "    payload: dict[str, object]\n"
            "\n"
            "\n"
            "class DurableJobHandler(Protocol):\n"
            "    async def handle(\n"
            "        self, execution: DurableJobExecution\n"
            "    ) -> dict[str, object] | None: ...\n"
            "\n"
            "\n"
            "class DurableJobMessageHandler:\n"
            "    def __init__(\n"
            "        self, session_registry: AsyncSessionRegistry, handler: DurableJobHandler\n"
            "    ) -> None:\n"
            "        self._session_registry = session_registry\n"
            "        self._handler = handler\n"
            "\n"
            "    async def handle(self, message: EventMessage) -> None:\n"
            "        payload = message.payload\n"
            "        job_id = str(payload['job_id'])\n"
            "        job_type = str(payload['job_type'])\n"
            "        run_key = str(payload['run_key'])\n"
            "        job_payload = payload['payload']\n"
            "        if not isinstance(job_payload, dict):\n"
            "            raise TypeError('durable job payload must be an object')\n"
            "        definition = JOB_DEFINITIONS.get(job_type)\n"
            "        if definition is None or message.event_type != definition.event_type:\n"
            "            raise ValueError('durable job message does not match a definition')\n"
            "\n"
            "        async with self._session_registry.session(\n"
            "            ShardTarget(store=definition.store)\n"
            "        ) as session:\n"
            "            repository = DurableJobRepository(session)\n"
            "            claimed = await repository.transition(\n"
            "                job_id=job_id,\n"
            "                expected_status=DurableJobStatus.REQUESTED,\n"
            "                status=DurableJobStatus.RUNNING,\n"
            "            )\n"
            "            if not claimed:\n"
            "                return\n"
            "\n"
            "        execution = DurableJobExecution(\n"
            "            job_id=job_id,\n"
            "            job_type=job_type,\n"
            "            run_key=run_key,\n"
            "            payload=job_payload,\n"
            "        )\n"
            "        try:\n"
            "            result = await self._handler.handle(execution)\n"
            "        except Exception as error:\n"
            "            async with self._session_registry.session(\n"
            "                ShardTarget(store=definition.store)\n"
            "            ) as session:\n"
            "                await DurableJobRepository(session).transition(\n"
            "                    job_id=job_id,\n"
            "                    expected_status=DurableJobStatus.RUNNING,\n"
            "                    status=DurableJobStatus.FAILED,\n"
            "                    error=str(error) or type(error).__name__,\n"
            "                )\n"
            "            raise\n"
            "\n"
            "        async with self._session_registry.session(\n"
            "            ShardTarget(store=definition.store)\n"
            "        ) as session:\n"
            "            completed = await DurableJobRepository(session).transition(\n"
            "                job_id=job_id,\n"
            "                expected_status=DurableJobStatus.RUNNING,\n"
            "                status=DurableJobStatus.SUCCEEDED,\n"
            "                result=result,\n"
            "            )\n"
            "        if not completed:\n"
            "            raise RuntimeError('durable job completion transition was lost')\n"
        )

    @staticmethod
    def _render_handler_scaffold(package: str) -> str:
        return (
            f"from {package}.infrastructure.database.session import AsyncSessionRegistry\n"
            f"from {package}.infrastructure.durable_jobs.worker import DurableJobExecution\n"
            "\n"
            "\n"
            "class ApplicationDurableJobHandler:\n"
            "    async def handle(\n"
            "        self, execution: DurableJobExecution\n"
            "    ) -> dict[str, object] | None:\n"
            "        raise NotImplementedError('implement the durable job business handler')\n"
            "\n"
            "\n"
            "def validate_durable_job_payload(\n"
            "    job_type: str, payload: dict[str, object]\n"
            ") -> None:\n"
            "    del job_type, payload\n"
            "\n"
            "\n"
            "def create_durable_job_handler(\n"
            "    session_registry: AsyncSessionRegistry,\n"
            ") -> ApplicationDurableJobHandler:\n"
            "    del session_registry\n"
            "    return ApplicationDurableJobHandler()\n"
        )

    @staticmethod
    def _render_worker_runner(
        specification: ProjectSpec,
        service: ServiceSpec,
    ) -> str:
        durable_stores = {job.store for job in specification.application.durable_jobs}
        database_environments = {
            database.name: database.global_url_env
            for database in specification.application.databases
            if database.name in durable_stores and database.global_url_env is not None
        }
        event_types = [job.event_type for job in specification.application.durable_jobs]
        package = specification.project.package_name
        heartbeat_stdlib_import = ""
        heartbeat_import = ""
        heartbeat_start = ""
        heartbeat_stop = ""
        if specification.application.control_plane_heartbeat.enabled:
            heartbeat_stdlib_import = "from contextlib import suppress\n"
            heartbeat_import = (
                f"from {package}.application.generated.service_heartbeat import (\n"
                "    run_service_heartbeat_reporter,\n"
                ")\n"
            )
            heartbeat_start = (
                "    heartbeat_task = asyncio.create_task(\n"
                "        run_service_heartbeat_reporter(\n"
                f"            service_name={package!r} + '-durable-job-worker',\n"
                "            dependencies={'database': 'ok', 'rabbitmq': 'ok'},\n"
                "        ),\n"
                "        name='durable-job-worker-heartbeat',\n"
                "    )\n"
            )
            heartbeat_stop = (
                "        heartbeat_task.cancel()\n"
                "        with suppress(asyncio.CancelledError):\n"
                "            await heartbeat_task\n"
            )
        return (
            "import asyncio\n"
            "import os\n"
            + heartbeat_stdlib_import
            + "\n"
            + "import aio_pika\n"
            "from sqlalchemy.ext.asyncio import create_async_engine\n"
            "\n"
            f"from {package}.application.durable_job_handler import (\n"
            "    create_durable_job_handler,\n"
            ")\n"
            + heartbeat_import
            + f"from {package}.application.observability import LOGGER, configure_logging\n"
            f"from {package}.infrastructure.database.session import AsyncSessionRegistry\n"
            f"from {package}.infrastructure.durable_jobs.worker import DurableJobMessageHandler\n"
            f"from {package}.infrastructure.messaging.rabbitmq import RabbitMQConsumer\n"
            "\n"
            f"RABBITMQ_URL_ENV = {json.dumps(service.connection_url_env)}\n"
            f"DURABLE_JOB_QUEUE = {json.dumps(service.queue + '.durable-jobs')}\n"
            f"DURABLE_JOB_EVENT_TYPES = {json.dumps(event_types)}\n"
            f"GLOBAL_DATABASE_URL_ENVS = {json.dumps(database_environments, sort_keys=True)}\n"
            "\n"
            "\n"
            "async def main() -> None:\n"
            "    configure_logging()\n"
            "    LOGGER.info('durable job worker starting')\n"
            "    engines = {\n"
            "        store: create_async_engine(os.environ[environment_name], pool_pre_ping=True)\n"
            "        for store, environment_name in GLOBAL_DATABASE_URL_ENVS.items()\n"
            "    }\n"
            "    registry = AsyncSessionRegistry(engines, {})\n"
            "    connection = await aio_pika.connect_robust(os.environ[RABBITMQ_URL_ENV])\n"
            "    consumer = RabbitMQConsumer(connection)\n"
            "    handler = DurableJobMessageHandler(\n"
            "        registry, create_durable_job_handler(registry)\n"
            "    )\n"
            + heartbeat_start
            + "    try:\n"
            "        await consumer.consume(\n"
            "            handler,\n"
            "            queue_name=DURABLE_JOB_QUEUE,\n"
            "            routing_keys=tuple(DURABLE_JOB_EVENT_TYPES),\n"
            "        )\n"
            "        await asyncio.Future()\n"
            "    finally:\n"
            + heartbeat_stop
            + "        await connection.close()\n"
            "        for engine in engines.values():\n"
            "            await engine.dispose()\n"
            "        LOGGER.info('durable job worker stopped')\n"
            "\n"
            "\n"
            "if __name__ == '__main__':\n"
            "    asyncio.run(main())\n"
        )

    @staticmethod
    def _render_airflow_dag(job: DurableJobSpec, token_env: str) -> str:
        payload_env = f"DURABLE_JOB_{job.name.upper()}_PAYLOAD_JSON"
        return (
            "\"\"\"Generated Airflow orchestration for a durable job.\"\"\"\n"
            "\n"
            "import json\n"
            "import os\n"
            "import time\n"
            "from datetime import UTC, datetime, timedelta\n"
            "from urllib.request import Request, urlopen\n"
            "\n"
            "from airflow.operators.python import PythonOperator, get_current_context\n"
            "\n"
            "from airflow import DAG\n"
            "\n"
            f"JOB_TYPE = {job.name!r}\n"
            f"PAYLOAD_ENV = {payload_env!r}\n"
            "POLL_SECONDS = int(os.getenv('DURABLE_JOB_POLL_SECONDS', '5'))\n"
            "TIMEOUT_SECONDS = int(os.getenv('DURABLE_JOB_TIMEOUT_SECONDS', '3600'))\n"
            "\n"
            "\n"
            "def _request(method: str, path: str, body: dict[str, object] | None = None) -> dict[str, object]:\n"
            "    base_url = os.environ['DURABLE_JOB_API_URL'].rstrip('/')\n"
            f"    api_token = os.environ[{token_env!r}]\n"
            "    data = json.dumps(body).encode() if body is not None else None\n"
            "    request = Request(\n"
            "        f'{base_url}{path}', data=data, method=method,\n"
            "        headers={\n"
            "            'Authorization': f'Bearer {api_token}',\n"
            "            'Content-Type': 'application/json',\n"
            "        },\n"
            "    )\n"
            "    with urlopen(request, timeout=TIMEOUT_SECONDS) as response:\n"
            "        payload = json.load(response)\n"
            "    if not isinstance(payload, dict):\n"
            "        raise TypeError('durable job API response must be an object')\n"
            "    return payload\n"
            "\n"
            "\n"
            "def _payload() -> dict[str, object]:\n"
            "    payload = json.loads(os.getenv(PAYLOAD_ENV, '{}'))\n"
            "    if not isinstance(payload, dict):\n"
            "        raise TypeError(f'{PAYLOAD_ENV} must contain a JSON object')\n"
            "    return payload\n"
            "\n"
            "\n"
            "def trigger_job() -> str:\n"
            "    data_interval_start = get_current_context()['data_interval_start']\n"
            "    if data_interval_start is None:\n"
            "        raise RuntimeError('Airflow data interval start is required')\n"
            "    run_key = f'{JOB_TYPE}:{data_interval_start.isoformat()}'\n"
            "    response = _request(\n"
            "        'POST', f'/internal/jobs/{JOB_TYPE}',\n"
            "        {'run_key': run_key, 'payload': _payload()},\n"
            "    )\n"
            "    return str(response['job_id'])\n"
            "\n"
            "\n"
            "def wait_for_job(ti) -> None:\n"
            "    job_id = str(ti.xcom_pull(task_ids='trigger'))\n"
            "    while True:\n"
            "        response = _request('GET', f'/internal/jobs/{JOB_TYPE}/{job_id}')\n"
            "        status = str(response['status'])\n"
            "        if status == 'succeeded':\n"
            "            return\n"
            "        if status == 'failed':\n"
            "            raise RuntimeError(str(response.get('error') or 'durable job failed'))\n"
            "        if status == 'cancelled':\n"
            "            raise RuntimeError('durable job cancelled')\n"
            "        time.sleep(POLL_SECONDS)\n"
            "\n"
            "\n"
            "with DAG(\n"
            f"    dag_id='durable_job_{job.name}',\n"
            f"    schedule={job.schedule!r},\n"
            "    start_date=datetime(2024, 1, 1, tzinfo=UTC),\n"
            "    catchup=False,\n"
            "    default_args={'retries': 3, 'retry_delay': timedelta(minutes=1)},\n"
            ") as dag:\n"
            "    trigger = PythonOperator(task_id='trigger', python_callable=trigger_job)\n"
            "    wait = PythonOperator(\n"
            "        task_id='wait',\n"
            "        python_callable=wait_for_job,\n"
            "        execution_timeout=timedelta(seconds=TIMEOUT_SECONDS),\n"
            "    )\n"
            "    trigger >> wait\n"
        )

    @staticmethod
    def _render_revision(store: str) -> str:
        revision = alembic_revision_id(f"af_{store}_durable_jobs_0001")
        down_revision = alembic_revision_id(f"af_{store}_outbox_0001")
        return (
            f'"""AutoForge durable jobs for {store}."""\n'
            "\n"
            "import sqlalchemy as sa\n"
            "from alembic import op\n"
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
