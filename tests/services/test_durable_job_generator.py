import ast
from pathlib import PurePosixPath

from autoforge.core.generation import FileOwnership
from autoforge.core.specification import (
    ApplicationSpec,
    DatabaseStoreSpec,
    DurableJobSpec,
    ProjectInfo,
    ProjectSpec,
    ServiceSpec,
)
from autoforge.services.generation.durable_jobs import DurableJobGenerator
from autoforge.services.generation.fastapi_project import FastAPIProjectGenerator


def durable_job_specification() -> ProjectSpec:
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
                    name="account", global_url_env="ACCOUNT_DATABASE_URL"
                )
            ],
            services=[
                ServiceSpec(
                    name="events",
                    kind="rabbitmq",
                    outbox_stores=["account"],
                )
            ],
            durable_jobs=[
                DurableJobSpec(
                    name="news_collection",
                    store="account",
                    event_type="news.collection.requested",
                    routing_key="news.collection.requested",
                )
            ],
        ),
    )


def test_durable_job_generator_emits_atomic_request_contract() -> None:
    files = DurableJobGenerator().render(durable_job_specification())

    expected = {
        PurePosixPath("src/kis_auto_trading/infrastructure/durable_jobs/__init__.py"),
        PurePosixPath("src/kis_auto_trading/infrastructure/durable_jobs/contracts.py"),
        PurePosixPath("src/kis_auto_trading/infrastructure/durable_jobs/models.py"),
        PurePosixPath("src/kis_auto_trading/infrastructure/durable_jobs/repository.py"),
        PurePosixPath("src/kis_auto_trading/infrastructure/durable_jobs/worker.py"),
        PurePosixPath("src/kis_auto_trading/application/durable_job_handler.py"),
        PurePosixPath("migrations/account/versions/0003_durable_jobs.py"),
    }
    assert set(files) == expected
    for path, content in files.items():
        if path.suffix == ".py":
            ast.parse(content)

    contracts = files[
        PurePosixPath("src/kis_auto_trading/infrastructure/durable_jobs/contracts.py")
    ]
    repository = files[
        PurePosixPath("src/kis_auto_trading/infrastructure/durable_jobs/repository.py")
    ]
    worker = files[
        PurePosixPath("src/kis_auto_trading/infrastructure/durable_jobs/worker.py")
    ]
    handler = files[
        PurePosixPath("src/kis_auto_trading/application/durable_job_handler.py")
    ]
    revision = files[PurePosixPath("migrations/account/versions/0003_durable_jobs.py")]

    assert "news.collection.requested" in contracts
    assert "on_conflict_do_nothing(index_elements=['job_type', 'run_key'])" in repository
    assert "OutboxWriter(self._session).add(" in repository
    assert ".commit(" not in repository
    assert "message.event_type != definition.event_type" in worker
    assert "DurableJobStatus.REQUESTED" in worker
    assert "DurableJobStatus.RUNNING" in worker
    assert "DurableJobStatus.SUCCEEDED" in worker
    assert "DurableJobStatus.FAILED" in worker
    assert "raise" in worker
    assert "class ApplicationDurableJobHandler" in handler
    assert "af_account_outbox_0001" in revision
    assert "uq_durable_jobs_type_run_key" in revision


def test_durable_job_migration_is_scaffolded() -> None:
    plan = DurableJobGenerator().plan(durable_job_specification())
    ownership = {item.relative_path: item.ownership for item in plan.files}

    assert ownership[
        PurePosixPath("migrations/account/versions/0003_durable_jobs.py")
    ] is FileOwnership.SCAFFOLDED
    assert ownership[
        PurePosixPath("src/kis_auto_trading/application/durable_job_handler.py")
    ] is FileOwnership.SCAFFOLDED


def test_fastapi_project_registers_durable_job_endpoints() -> None:
    files = FastAPIProjectGenerator().render(durable_job_specification())

    router = files[PurePosixPath("src/kis_auto_trading/routers/durable_jobs.py")]
    app_factory = files[
        PurePosixPath("src/kis_auto_trading/application/app_factory.py")
    ]

    ast.parse(router)
    ast.parse(app_factory)
    assert "@router.post(" in router
    assert "status.HTTP_202_ACCEPTED" in router
    assert "ShardTarget(store=definition.store)" in router
    assert "app.include_router(durable_jobs_router)" in app_factory
