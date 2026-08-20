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
from autoforge.core.specification import ProjectSpec, ServiceSpec

MESSAGING_GENERATOR_ID: Final = "autoforge.generator.service.messaging"
MESSAGING_GENERATOR_VERSION: Final = "0.1.0"


class MessagingGenerator:
    """Generate the RabbitMQ transport and transactional outbox runtime."""

    @property
    def generator_id(self) -> str:
        return MESSAGING_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return MESSAGING_GENERATOR_VERSION

    def render(self, specification: ProjectSpec) -> dict[PurePosixPath, str]:
        services = self._services(specification)
        if not services:
            return {}
        if len(services) != 1:
            raise ValueError(
                "Only one rabbitmq service is supported per application."
            )
        service = services[0]
        package = specification.project.package_name
        root = PurePosixPath("src", package, "infrastructure")
        files = {
            PurePosixPath(
                "src", package, "application", "message_topology.py"
            ): self._render_message_topology_scaffold(),
            root / "messaging" / "__init__.py": self._render_messaging_init(),
            root / "messaging" / "protocol.py": self._render_protocol(),
            root / "messaging" / "rabbitmq.py": self._render_rabbitmq(service),
            root / "outbox" / "__init__.py": self._render_outbox_init(),
            root / "outbox" / "inbox.py": self._render_inbox(package),
            root / "outbox" / "models.py": self._render_outbox_models(package),
            root / "outbox" / "repository.py": self._render_repository(package),
            root / "outbox" / "relay.py": self._render_relay(package),
            PurePosixPath("scripts", "run_outbox_relay.py"): self._render_relay_runner(
                specification, service
            ),
            PurePosixPath("scripts", "run_message_worker.py"): (
                self._render_worker_runner(package, service)
            ),
        }
        declared_stores = {
            store.name for store in specification.application.databases
        }
        unknown = sorted(set(service.outbox_stores) - declared_stores)
        if unknown:
            raise ValueError(
                f"rabbitmq outbox_stores are not declared databases: {unknown}"
            )
        for store in service.outbox_stores:
            files[
                PurePosixPath(
                    "migrations", store, "versions", "0002_outbox.py"
                )
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
                        if path.name
                        in {"message_topology.py", "run_message_worker.py"}
                        or (
                            len(path.parts) >= 3
                            and path.parts[0] == "migrations"
                            and path.parts[2] == "versions"
                        )
                        else FileOwnership.GENERATED
                    ),
                    action=PlannedAction.CREATE,
                    specification_hash=spec_hash,
                    expected_content_hash=content_hash(content),
                    source="project:rabbitmq-outbox",
                )
                for path, content in sorted(
                    rendered.items(), key=lambda item: item[0].as_posix()
                )
            ],
        )

    @staticmethod
    def _services(specification: ProjectSpec) -> list[ServiceSpec]:
        return [
            service
            for service in specification.application.services
            if service.kind == "rabbitmq"
        ]

    @staticmethod
    def _render_messaging_init() -> str:
        return (
            "from .protocol import (\n"
            "    EventMessage,\n"
            "    MessageHandler,\n"
            "    MessagePublisher,\n"
            "    MessagePublishError,\n"
            ")\n"
            "from .rabbitmq import RabbitMQConsumer, RabbitMQPublisher\n"
            "\n"
            "__all__ = [\n"
            '    "EventMessage",\n'
            '    "MessageHandler",\n'
            '    "MessagePublishError",\n'
            '    "MessagePublisher",\n'
            '    "RabbitMQConsumer",\n'
            '    "RabbitMQPublisher",\n'
            "]\n"
        )

    @staticmethod
    def _render_protocol() -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "from dataclasses import dataclass\n"
            "from datetime import UTC, datetime\n"
            "from typing import Protocol\n"
            "from uuid import uuid4\n"
            "\n"
            "\n"
            "@dataclass(frozen=True, slots=True)\n"
            "class EventMessage:\n"
            "    event_type: str\n"
            "    aggregate_id: str\n"
            "    payload: dict[str, object]\n"
            "    routing_key: str\n"
            "    event_id: str = \"\"\n"
            "    event_version: int = 1\n"
            "    occurred_at: datetime | None = None\n"
            "\n"
            "    def __post_init__(self) -> None:\n"
            "        if not self.event_id:\n"
            "            object.__setattr__(self, 'event_id', str(uuid4()))\n"
            "        if self.occurred_at is None:\n"
            "            object.__setattr__(self, 'occurred_at', datetime.now(UTC))\n"
            "\n"
            "\n"
            "class MessagePublisher(Protocol):\n"
            "    async def publish(self, message: EventMessage) -> None: ...\n"
            "\n"
            "\n"
            "class MessagePublishError(RuntimeError):\n"
            "    pass\n"
            "\n"
            "\n"
            "class MessageHandler(Protocol):\n"
            "    async def handle(self, message: EventMessage) -> None: ...\n"
        )

    @staticmethod
    def _render_rabbitmq(service: ServiceSpec) -> str:
        queue_arguments = "{'x-dead-letter-exchange': DEAD_LETTER_EXCHANGE}"
        dead_letter_queue_arguments = "{}"
        if service.queue_type == "quorum":
            queue_arguments = (
                "{'x-queue-type': 'quorum', "
                "'x-dead-letter-exchange': DEAD_LETTER_EXCHANGE}"
            )
            dead_letter_queue_arguments = "{'x-queue-type': 'quorum'}"
        return (
            "from __future__ import annotations\n"
            "\n"
            "import json\n"
            "import logging\n"
            "from datetime import datetime\n"
            "\n"
            "import aio_pika\n"
            "from aio_pika.abc import (\n"
            "    AbstractIncomingMessage,\n"
            "    AbstractRobustConnection,\n"
            "    AbstractRobustExchange,\n"
            "    AbstractRobustQueue,\n"
            ")\n"
            "from aio_pika.exceptions import CONNECTION_EXCEPTIONS\n"
            "\n"
            "from .protocol import EventMessage, MessageHandler, MessagePublishError\n"
            "\n"
            "logger = logging.getLogger(__name__)\n"
            "\n"
            f"EXCHANGE_NAME = {json.dumps(service.exchange)}\n"
            f"QUEUE_NAME = {json.dumps(service.queue)}\n"
            f"ROUTING_KEY = {json.dumps(service.routing_key)}\n"
            f"DEAD_LETTER_EXCHANGE = {json.dumps(service.dead_letter_exchange)}\n"
            f"DEAD_LETTER_QUEUE = {json.dumps(service.dead_letter_queue)}\n"
            f"QUEUE_TYPE = {json.dumps(service.queue_type)}\n"
            f"QUEUE_ARGUMENTS = {queue_arguments}\n"
            f"DEAD_LETTER_QUEUE_ARGUMENTS = {dead_letter_queue_arguments}\n"
            f"PREFETCH_COUNT = {service.prefetch_count}\n"
            "\n"
            "\n"
            "async def declare_topology(\n"
            "    connection: AbstractRobustConnection,\n"
            "    *,\n"
            "    queue_name: str = QUEUE_NAME,\n"
            "    routing_keys: tuple[str, ...] = (ROUTING_KEY,),\n"
            ") -> tuple[AbstractRobustExchange, AbstractRobustQueue]:\n"
            "    channel = await connection.channel(\n"
            "        publisher_confirms=True, on_return_raises=True\n"
            "    )\n"
            "    await channel.set_qos(prefetch_count=PREFETCH_COUNT)\n"
            "    dead_letter_exchange = await channel.declare_exchange(\n"
            "        DEAD_LETTER_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True\n"
            "    )\n"
            "    dead_letter_queue = await channel.declare_queue(\n"
            "        DEAD_LETTER_QUEUE, durable=True, arguments=DEAD_LETTER_QUEUE_ARGUMENTS\n"
            "    )\n"
            "    await dead_letter_queue.bind(dead_letter_exchange, routing_key='#')\n"
            "    exchange = await channel.declare_exchange(\n"
            "        EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True\n"
            "    )\n"
            "    queue = await channel.declare_queue(\n"
            "        queue_name,\n"
            "        durable=True,\n"
            "        arguments=QUEUE_ARGUMENTS,\n"
            "    )\n"
            "    for routing_key in routing_keys:\n"
            "        await queue.bind(exchange, routing_key=routing_key)\n"
            "    return exchange, queue\n"
            "\n"
            "\n"
            "class RabbitMQPublisher:\n"
            "    def __init__(self, connection: AbstractRobustConnection) -> None:\n"
            "        self._connection = connection\n"
            "        self._exchange: AbstractRobustExchange | None = None\n"
            "\n"
            "    async def start(self) -> None:\n"
            "        self._exchange, _ = await declare_topology(self._connection)\n"
            "\n"
            "    async def publish(self, message: EventMessage) -> None:\n"
            "        if self._exchange is None:\n"
            "            await self.start()\n"
            "        assert self._exchange is not None\n"
            "        occurred_at = message.occurred_at\n"
            "        assert occurred_at is not None\n"
            "        body = json.dumps(\n"
            "            {\n"
            "                'event_id': message.event_id,\n"
            "                'event_type': message.event_type,\n"
            "                'event_version': message.event_version,\n"
            "                'aggregate_id': message.aggregate_id,\n"
            "                'payload': message.payload,\n"
            "                'routing_key': message.routing_key,\n"
            "                'occurred_at': occurred_at.isoformat(),\n"
            "            },\n"
            "            separators=(',', ':'),\n"
            "            sort_keys=True,\n"
            "        ).encode('utf-8')\n"
            "        try:\n"
            "            await self._exchange.publish(\n"
            "                aio_pika.Message(\n"
            "                    body=body,\n"
            "                    message_id=message.event_id,\n"
            "                    type=message.event_type,\n"
            "                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,\n"
            "                    content_type='application/json',\n"
            "                ),\n"
            "                routing_key=message.routing_key,\n"
            "                mandatory=True,\n"
            "            )\n"
            "        except CONNECTION_EXCEPTIONS as error:\n"
            "            raise MessagePublishError(str(error)) from error\n"
            "\n"
            "\n"
            "class RabbitMQConsumer:\n"
            "    def __init__(self, connection: AbstractRobustConnection) -> None:\n"
            "        self._connection = connection\n"
            "\n"
            "    async def consume(\n"
            "        self,\n"
            "        handler: MessageHandler,\n"
            "        *,\n"
            "        queue_name: str = QUEUE_NAME,\n"
            "        routing_keys: tuple[str, ...] = (ROUTING_KEY,),\n"
            "    ) -> None:\n"
            "        _, queue = await declare_topology(\n"
            "            self._connection, queue_name=queue_name, routing_keys=routing_keys\n"
            "        )\n"
            "\n"
            "        async def process(message: AbstractIncomingMessage) -> None:\n"
            "            try:\n"
            "                async with message.process(requeue=False):\n"
            "                    decoded = json.loads(message.body.decode('utf-8'))\n"
            "                    await handler.handle(\n"
            "                        EventMessage(\n"
            "                            event_id=decoded['event_id'],\n"
            "                            event_type=decoded['event_type'],\n"
            "                            event_version=decoded['event_version'],\n"
            "                            aggregate_id=decoded['aggregate_id'],\n"
            "                            payload=decoded['payload'],\n"
            "                            routing_key=decoded['routing_key'],\n"
            "                            occurred_at=datetime.fromisoformat(\n"
            "                                decoded['occurred_at']\n"
            "                            ),\n"
            "                        )\n"
            "                    )\n"
            "            except Exception:\n"
            "                logger.exception(\n"
            "                    'message rejected after handler failure',\n"
            "                    extra={'message_id': message.message_id},\n"
            "                )\n"
            "\n"
            "        await queue.consume(process, no_ack=False)\n"
        )

    @staticmethod
    def _render_outbox_init() -> str:
        return (
            "from .inbox import ProcessedMessageInbox\n"
            "from .relay import OutboxRelay\n"
            "from .repository import OutboxWriter\n"
            "\n"
            "__all__ = [\n"
            '    "OutboxRelay",\n'
            '    "OutboxWriter",\n'
            '    "ProcessedMessageInbox",\n'
            "]\n"
        )

    @staticmethod
    def _render_inbox(package: str) -> str:
        return (
            "from datetime import UTC, datetime\n"
            "\n"
            "from sqlalchemy.dialects.postgresql import insert\n"
            "from sqlalchemy.ext.asyncio import AsyncSession\n"
            "\n"
            f"from {package}.infrastructure.outbox.models import (\n"
            "    ProcessedMessageRecord,\n"
            ")\n"
            "\n"
            "\n"
            "class ProcessedMessageInbox:\n"
            "    def __init__(self, session: AsyncSession) -> None:\n"
            "        self._session = session\n"
            "\n"
            "    async def claim(self, event_id: str) -> bool:\n"
            "        statement = (\n"
            "            insert(ProcessedMessageRecord)\n"
            "            .values(event_id=event_id, processed_at=datetime.now(UTC))\n"
            "            .on_conflict_do_nothing(index_elements=['event_id'])\n"
            "        )\n"
            "        result = await self._session.execute(statement)\n"
            "        return result.rowcount == 1\n"
        )

    @staticmethod
    def _render_outbox_models(package: str) -> str:
        return (
            "from datetime import datetime\n"
            "\n"
            "from sqlalchemy import DateTime, Integer, String, Text\n"
            "from sqlalchemy.dialects.postgresql import JSONB, UUID\n"
            "from sqlalchemy.orm import Mapped, mapped_column\n"
            "\n"
            f"from {package}.infrastructure.database.base import Base\n"
            "\n"
            "\n"
            "class OutboxEventRecord(Base):\n"
            "    __tablename__ = 'outbox_events'\n"
            "\n"
            "    event_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)\n"
            "    event_type: Mapped[str] = mapped_column(String(200), nullable=False)\n"
            "    event_version: Mapped[int] = mapped_column(Integer, nullable=False)\n"
            "    aggregate_id: Mapped[str] = mapped_column(String(200), nullable=False)\n"
            "    routing_key: Mapped[str] = mapped_column(String(200), nullable=False)\n"
            "    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)\n"
            "    status: Mapped[str] = mapped_column(String(20), nullable=False)\n"
            "    attempts: Mapped[int] = mapped_column(Integer, nullable=False)\n"
            "    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)\n"
            "    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)\n"
            "    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))\n"
            "    last_error: Mapped[str | None] = mapped_column(Text)\n"
            "\n"
            "\n"
            "class ProcessedMessageRecord(Base):\n"
            "    __tablename__ = 'processed_messages'\n"
            "\n"
            "    event_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)\n"
            "    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)\n"
        )

    @staticmethod
    def _render_repository(package: str) -> str:
        return (
            "from datetime import UTC, datetime\n"
            "\n"
            "from sqlalchemy.ext.asyncio import AsyncSession\n"
            "\n"
            f"from {package}.infrastructure.messaging.protocol import EventMessage\n"
            f"from {package}.infrastructure.outbox.models import OutboxEventRecord\n"
            "\n"
            "\n"
            "class OutboxWriter:\n"
            "    def __init__(self, session: AsyncSession) -> None:\n"
            "        self._session = session\n"
            "\n"
            "    def add(\n"
            "        self, message: EventMessage, *, available_at: datetime | None = None\n"
            "    ) -> None:\n"
            "        occurred_at = message.occurred_at or datetime.now(UTC)\n"
            "        self._session.add(\n"
            "            OutboxEventRecord(\n"
            "                event_id=message.event_id,\n"
            "                event_type=message.event_type,\n"
            "                event_version=message.event_version,\n"
            "                aggregate_id=message.aggregate_id,\n"
            "                routing_key=message.routing_key,\n"
            "                payload=message.payload,\n"
            "                status='pending',\n"
            "                attempts=0,\n"
            "                available_at=available_at or occurred_at,\n"
            "                occurred_at=occurred_at,\n"
            "            )\n"
            "        )\n"
        )

    @staticmethod
    def _render_relay(package: str) -> str:
        return (
            "from datetime import UTC, datetime, timedelta\n"
            "\n"
            "from sqlalchemy import select\n"
            "from sqlalchemy.ext.asyncio import AsyncSession\n"
            "\n"
            f"from {package}.infrastructure.messaging.protocol import (\n"
            "    EventMessage,\n"
            "    MessagePublisher,\n"
            "    MessagePublishError,\n"
            ")\n"
            f"from {package}.infrastructure.outbox.models import OutboxEventRecord\n"
            "\n"
            "\n"
            "class OutboxRelay:\n"
            "    def __init__(self, publisher: MessagePublisher, batch_size: int = 100) -> None:\n"
            "        self._publisher = publisher\n"
            "        self._batch_size = batch_size\n"
            "\n"
            "    async def publish_pending(self, session: AsyncSession) -> int:\n"
            "        now = datetime.now(UTC)\n"
            "        result = await session.execute(\n"
            "            select(OutboxEventRecord)\n"
            "            .where(\n"
            "                OutboxEventRecord.status == 'pending',\n"
            "                OutboxEventRecord.available_at <= now,\n"
            "            )\n"
            "            .order_by(OutboxEventRecord.occurred_at)\n"
            "            .limit(self._batch_size)\n"
            "            .with_for_update(skip_locked=True)\n"
            "        )\n"
            "        records = list(result.scalars())\n"
            "        published = 0\n"
            "        for record in records:\n"
            "            record.attempts += 1\n"
            "            try:\n"
            "                await self._publisher.publish(\n"
            "                    EventMessage(\n"
            "                        event_id=record.event_id,\n"
            "                        event_type=record.event_type,\n"
            "                        event_version=record.event_version,\n"
            "                        aggregate_id=record.aggregate_id,\n"
            "                        payload=record.payload,\n"
            "                        routing_key=record.routing_key,\n"
            "                        occurred_at=record.occurred_at,\n"
            "                    )\n"
            "                )\n"
            "            except MessagePublishError as error:\n"
            "                record.last_error = str(error)[:2000]\n"
            "                delay = min(60, 2 ** min(record.attempts, 6))\n"
            "                record.available_at = now + timedelta(seconds=delay)\n"
            "            else:\n"
            "                record.status = 'published'\n"
            "                record.published_at = datetime.now(UTC)\n"
            "                record.last_error = None\n"
            "                published += 1\n"
            "        return published\n"
        )

    @staticmethod
    def _render_relay_runner(
        specification: ProjectSpec, service: ServiceSpec
    ) -> str:
        targets = [
            environment_name
            for store in specification.application.databases
            if store.name in service.outbox_stores
            for environment_name in (
                ([store.global_url_env] if store.global_url_env else [])
                + [shard.url_env for shard in store.shards]
            )
        ]
        package = specification.project.package_name
        return (
            "import asyncio\n"
            "import os\n"
            "\n"
            "import aio_pika\n"
            "from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine\n"
            "\n"
            f"from {package}.application.observability import (\n"
            "    LOGGER,\n"
            "    configure_logging,\n"
            ")\n"
            f"from {package}.application.message_topology import (\n"
            "    declare_user_message_topology,\n"
            ")\n"
            f"from {package}.infrastructure.messaging.rabbitmq import RabbitMQPublisher\n"
            f"from {package}.infrastructure.outbox.relay import OutboxRelay\n"
            "\n"
            f"DATABASE_URL_ENVS = {json.dumps(targets)}\n"
            f"RABBITMQ_URL_ENV = {json.dumps(service.connection_url_env)}\n"
            "\n"
            "\n"
            "async def main() -> None:\n"
            "    configure_logging()\n"
            "    LOGGER.info('outbox relay starting')\n"
            "    rabbitmq_url = os.environ[RABBITMQ_URL_ENV]\n"
            "    connection = await aio_pika.connect_robust(rabbitmq_url)\n"
            "    publisher = RabbitMQPublisher(connection)\n"
            "    await publisher.start()\n"
            "    await declare_user_message_topology(connection)\n"
            "    engines = [\n"
            "        create_async_engine(os.environ[name], pool_pre_ping=True)\n"
            "        for name in DATABASE_URL_ENVS\n"
            "    ]\n"
            "    relay = OutboxRelay(publisher)\n"
            "    try:\n"
            "        while True:\n"
            "            published = 0\n"
            "            for engine in engines:\n"
            "                factory = async_sessionmaker(engine, expire_on_commit=False)\n"
            "                async with factory() as session, session.begin():\n"
            "                    published += await relay.publish_pending(session)\n"
            "            if published == 0:\n"
            "                await asyncio.sleep(1)\n"
            "    finally:\n"
            "        for engine in engines:\n"
            "            await engine.dispose()\n"
            "        await connection.close()\n"
            "        LOGGER.info('outbox relay stopped')\n"
            "\n"
            "\n"
            "if __name__ == '__main__':\n"
            "    asyncio.run(main())\n"
        )

    @staticmethod
    def _render_message_topology_scaffold() -> str:
        return (
            "from aio_pika.abc import AbstractRobustConnection\n"
            "\n"
            "\n"
            "async def declare_user_message_topology(\n"
            "    connection: AbstractRobustConnection,\n"
            ") -> None:\n"
            "    del connection\n"
        )

    @staticmethod
    def _render_worker_runner(package: str, service: ServiceSpec) -> str:
        return (
            "import asyncio\n"
            "import os\n"
            "\n"
            "import aio_pika\n"
            "\n"
            f"from {package}.application.observability import (\n"
            "    LOGGER,\n"
            "    configure_logging,\n"
            ")\n"
            f"from {package}.infrastructure.messaging.protocol import EventMessage\n"
            f"from {package}.infrastructure.messaging.rabbitmq import RabbitMQConsumer\n"
            "\n"
            f"RABBITMQ_URL_ENV = {json.dumps(service.connection_url_env)}\n"
            "\n"
            "\n"
            "class ApplicationMessageHandler:\n"
            "    async def handle(self, message: EventMessage) -> None:\n"
            "        LOGGER.info('message received', extra={'event_id': message.event_id})\n"
            "\n"
            "\n"
            "async def main() -> None:\n"
            "    configure_logging()\n"
            "    LOGGER.info('message worker starting')\n"
            "    connection = await aio_pika.connect_robust(\n"
            "        os.environ[RABBITMQ_URL_ENV]\n"
            "    )\n"
            "    consumer = RabbitMQConsumer(connection)\n"
            "    try:\n"
            "        await consumer.consume(ApplicationMessageHandler())\n"
            "        await asyncio.Future()\n"
            "    finally:\n"
            "        await connection.close()\n"
            "        LOGGER.info('message worker stopped')\n"
            "\n"
            "\n"
            "if __name__ == '__main__':\n"
            "    asyncio.run(main())\n"
        )

    @staticmethod
    def _render_revision(store: str) -> str:
        revision = f"af_{store}_outbox_0001"
        return (
            f'"""AutoForge transactional outbox for {store}."""\n'
            "\n"
            "import sqlalchemy as sa\n"
            "from alembic import op\n"
            "from sqlalchemy.dialects import postgresql\n"
            "\n"
            f"revision = {revision!r}\n"
            "down_revision = None\n"
            f"branch_labels = ({(store + '_outbox')!r},)\n"
            "depends_on = None\n"
            "\n"
            "\n"
            "def upgrade() -> None:\n"
            "    op.create_table(\n"
            "        'outbox_events',\n"
            "        sa.Column('event_id', postgresql.UUID(as_uuid=False), primary_key=True),\n"
            "        sa.Column('event_type', sa.String(200), nullable=False),\n"
            "        sa.Column('event_version', sa.Integer(), nullable=False),\n"
            "        sa.Column('aggregate_id', sa.String(200), nullable=False),\n"
            "        sa.Column('routing_key', sa.String(200), nullable=False),\n"
            "        sa.Column('payload', postgresql.JSONB(), nullable=False),\n"
            "        sa.Column('status', sa.String(20), nullable=False),\n"
            "        sa.Column('attempts', sa.Integer(), nullable=False),\n"
            "        sa.Column('available_at', sa.DateTime(timezone=True), nullable=False),\n"
            "        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),\n"
            "        sa.Column('published_at', sa.DateTime(timezone=True)),\n"
            "        sa.Column('last_error', sa.Text()),\n"
            "    )\n"
            "    op.create_index(\n"
            "        'ix_outbox_pending', 'outbox_events', ['status', 'available_at']\n"
            "    )\n"
            "    op.create_table(\n"
            "        'processed_messages',\n"
            "        sa.Column('event_id', postgresql.UUID(as_uuid=False), primary_key=True),\n"
            "        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=False),\n"
            "    )\n"
            "\n"
            "\n"
            "def downgrade() -> None:\n"
            "    op.drop_table('processed_messages')\n"
            "    op.drop_index('ix_outbox_pending', table_name='outbox_events')\n"
            "    op.drop_table('outbox_events')\n"
        )
