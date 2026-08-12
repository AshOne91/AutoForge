import ast
from pathlib import PurePosixPath

import pytest

from autoforge.core.generation import FileOwnership, Generator
from autoforge.core.specification import (
    ApplicationSpec,
    DatabaseShardSpec,
    DatabaseStoreSpec,
    ProjectInfo,
    ProjectSpec,
    ServiceSpec,
)
from autoforge.services.generation.messaging import MessagingGenerator


def messaging_specification() -> ProjectSpec:
    return ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="KIS Auto Trading",
            package_name="kis_auto_trading",
            version="0.1.0",
        ),
        application=ApplicationSpec(
            databases=[
                DatabaseStoreSpec(
                    name="account",
                    shards=[
                        DatabaseShardSpec(
                            shard_id="1", url_env="ACCOUNT_SHARD_1_URL"
                        ),
                        DatabaseShardSpec(
                            shard_id="2", url_env="ACCOUNT_SHARD_2_URL"
                        ),
                    ],
                )
            ],
            services=[
                ServiceSpec(
                    name="events",
                    kind="rabbitmq",
                    connection_url_env="KIS_RABBITMQ_URL",
                    exchange="kis.events",
                    queue="kis.profile.worker",
                    routing_key="account.#",
                    outbox_stores=["account"],
                )
            ],
        ),
    )


def test_messaging_generator_satisfies_protocol() -> None:
    generator: Generator[ProjectSpec] = MessagingGenerator()

    assert isinstance(generator, Generator)


def test_render_generates_transport_outbox_relay_and_migration() -> None:
    files = MessagingGenerator().render(messaging_specification())

    expected = {
        PurePosixPath("src/kis_auto_trading/infrastructure/messaging/__init__.py"),
        PurePosixPath("src/kis_auto_trading/infrastructure/messaging/protocol.py"),
        PurePosixPath("src/kis_auto_trading/infrastructure/messaging/rabbitmq.py"),
        PurePosixPath("src/kis_auto_trading/infrastructure/outbox/__init__.py"),
        PurePosixPath("src/kis_auto_trading/infrastructure/outbox/inbox.py"),
        PurePosixPath("src/kis_auto_trading/infrastructure/outbox/models.py"),
        PurePosixPath("src/kis_auto_trading/infrastructure/outbox/repository.py"),
        PurePosixPath("src/kis_auto_trading/infrastructure/outbox/relay.py"),
        PurePosixPath("scripts/run_outbox_relay.py"),
        PurePosixPath("scripts/run_message_worker.py"),
        PurePosixPath("migrations/account/versions/0002_outbox.py"),
    }
    assert set(files) == expected
    for path, content in files.items():
        if path.suffix == ".py":
            ast.parse(content)

    rabbitmq = files[
        PurePosixPath(
            "src/kis_auto_trading/infrastructure/messaging/rabbitmq.py"
        )
    ]
    relay = files[
        PurePosixPath("src/kis_auto_trading/infrastructure/outbox/relay.py")
    ]
    inbox = files[
        PurePosixPath("src/kis_auto_trading/infrastructure/outbox/inbox.py")
    ]
    revision = files[
        PurePosixPath("migrations/account/versions/0002_outbox.py")
    ]
    assert "publisher_confirms=True" in rabbitmq
    assert "mandatory=True" in rabbitmq
    assert "queue_name: str = QUEUE_NAME" in rabbitmq
    assert "routing_keys: tuple[str, ...] = (ROUTING_KEY,)" in rabbitmq
    assert "for routing_key in routing_keys:" in rabbitmq
    assert "except CONNECTION_EXCEPTIONS as error" in rabbitmq
    assert "raise MessagePublishError" in rabbitmq
    assert "message.process(requeue=False)" in rabbitmq
    assert "message rejected after handler failure" in rabbitmq
    relay_runner = files[PurePosixPath("scripts/run_outbox_relay.py")]
    worker_runner = files[PurePosixPath("scripts/run_message_worker.py")]
    assert "configure_logging()" in relay_runner
    assert "configure_logging()" in worker_runner
    assert "LOGGER.info('outbox relay starting')" in relay_runner
    assert "LOGGER.info('message worker starting')" in worker_runner
    assert ".with_for_update(skip_locked=True)" in relay
    assert "except MessagePublishError as error" in relay
    assert "except Exception" not in relay
    repository = files[
        PurePosixPath("src/kis_auto_trading/infrastructure/outbox/repository.py")
    ]
    assert "available_at: datetime | None = None" in repository
    assert "available_at=available_at or occurred_at" in repository
    assert ".on_conflict_do_nothing(index_elements=['event_id'])" in inbox
    assert "af_account_outbox_0001" in revision
    assert "processed_messages" in revision


def test_worker_runner_is_scaffolded_and_other_files_are_generated() -> None:
    plan = MessagingGenerator().plan(messaging_specification())
    ownership = {file.relative_path: file.ownership for file in plan.files}

    assert ownership[PurePosixPath("scripts/run_message_worker.py")] is (
        FileOwnership.SCAFFOLDED
    )
    assert ownership[
        PurePosixPath("migrations/account/versions/0002_outbox.py")
    ] is FileOwnership.SCAFFOLDED
    assert all(
        value is FileOwnership.GENERATED
        for path, value in ownership.items()
        if path
        not in {
            PurePosixPath("scripts/run_message_worker.py"),
            PurePosixPath("migrations/account/versions/0002_outbox.py"),
        }
    )


def test_same_messaging_specification_is_reproducible() -> None:
    generator = MessagingGenerator()
    specification = messaging_specification()

    assert generator.render(specification) == generator.render(specification)
    assert generator.plan(specification) == generator.plan(specification)


def test_multiple_rabbitmq_services_are_rejected() -> None:
    specification = messaging_specification()
    service = specification.application.services[0]
    duplicate = service.model_copy(update={"name": "other_events"})
    specification = specification.model_copy(
        update={
            "application": specification.application.model_copy(
                update={"services": [service, duplicate]}
            )
        }
    )

    with pytest.raises(ValueError, match="Only one rabbitmq service"):
        MessagingGenerator().render(specification)
