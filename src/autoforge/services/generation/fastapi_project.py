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

GENERATOR_ID: Final = "autoforge.generator.fastapi.project"
GENERATOR_VERSION: Final = "0.1.0"


class FastAPIProjectGenerator:
    @property
    def generator_id(self) -> str:
        return GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return GENERATOR_VERSION

    def render(
        self,
        specification: ProjectSpec,
    ) -> dict[PurePosixPath, str]:
        project = specification.project
        package_name = project.package_name
        package_root = PurePosixPath("src", package_name)
        session_services = [
            service
            for service in specification.application.services
            if service.kind == "redis_session"
        ]
        database_stores = specification.application.databases
        has_database = bool(database_stores)
        has_session_store = bool(session_services)
        has_durable_jobs = bool(specification.application.durable_jobs)
        heartbeat = specification.application.control_plane_heartbeat
        has_heartbeat_reporter = heartbeat.enabled
        database_provider = specification.tooling.local_environment.database_provider
        database_env_names = [
            environment_name
            for store in database_stores
            for environment_name in [
                store.global_url_env,
                *(shard.url_env for shard in store.shards),
            ]
            if environment_name is not None
        ]

        rendered = {
            PurePosixPath(".gitignore"): self._render_gitignore(),
            PurePosixPath("pyproject.toml"): self._render_pyproject(
                package_name=package_name,
                version=project.version,
                description=project.description,
                dependencies=project.dependencies,
                include_redis=any(
                    service.kind == "redis_session"
                    for service in specification.application.services
                ),
                include_rabbitmq=any(
                    service.kind == "rabbitmq"
                    for service in specification.application.services
                ),
                database_provider=database_provider,
                ruff_exclude=specification.tooling.ruff_exclude,
            ),
            PurePosixPath("README.md"): self._render_readme(
                project_name=project.name,
                description=project.description,
                package_name=package_name,
            ),
            package_root / "__init__.py": (f'__version__ = "{project.version}"\n'),
            package_root / "modules" / "__init__.py": "",
            package_root / "main.py": self._render_main(package_name),
            package_root
            / "application"
            / "observability.py": self._render_observability(package_name),
            package_root / "application" / "__init__.py": "",
            package_root
            / "application"
            / "extensions.py": self._render_extension_routers(),
            package_root / "application" / "generated" / "__init__.py": "",
            package_root
            / "application"
            / "generated"
            / "module_registry.py": self._render_module_registry(
                package_name=package_name,
                module_names=specification.application.modules,
            ),
            package_root / "application" / "app_factory.py": self._render_app_factory(
                package_name=package_name,
                project_name=project.name,
                version=project.version,
                has_durable_jobs=has_durable_jobs,
            ),
            package_root / "routers" / "__init__.py": "",
            package_root / "routers" / "health.py": self._render_health_router(
                package_name=package_name,
                has_database=has_database,
                has_session_store=has_session_store,
            ),
            PurePosixPath("tests", "test_health.py"): self._render_health_test(
                package_name,
                redis_env_values=[
                    self._redis_test_environment(service)
                    for service in session_services
                ],
                database_env_names=database_env_names,
                database_provider=database_provider,
                has_database=has_database,
                has_session_store=has_session_store,
            ),
        }
        rendered[
            package_root / "application" / "generated" / "lifespan.py"
        ] = self._render_lifespan(
            package_name,
            has_database=has_database,
            has_session_store=has_session_store,
            has_heartbeat_reporter=has_heartbeat_reporter,
        )
        if has_heartbeat_reporter:
            rendered[
                package_root / "application" / "generated" / "service_heartbeat.py"
            ] = self._render_service_heartbeat_reporter(
                package_name=package_name,
                service_name=package_name,
                deployed_version=project.version,
                endpoint_env=heartbeat.endpoint_env,
                token_env=heartbeat.token_env,
                interval_seconds=heartbeat.interval_seconds,
                dependencies={
                    **({"database": "ok"} if has_database else {}),
                    **({"session_store": "ok"} if has_session_store else {}),
                },
            )
        if has_durable_jobs:
            rendered[package_root / "routers" / "durable_jobs.py"] = (
                self._render_durable_jobs_router(package_name)
            )
        return rendered

    @staticmethod
    def _redis_test_environment(service: ServiceSpec) -> tuple[str, str]:
        if service.mode == "sentinel":
            return service.sentinel_urls_env, "localhost:26379"
        if service.mode == "cluster":
            return service.cluster_url_env, "redis://localhost:16379"
        return service.url_env, "redis://localhost:6379/0"

    def plan(self, specification: ProjectSpec) -> GenerationPlan:
        rendered_files = self.render(specification)
        spec_hash = specification_hash(specification)

        files = [
            PlannedFile(
                relative_path=relative_path,
                generator_id=self.generator_id,
                generator_version=self.generator_version,
                ownership=self._ownership(relative_path),
                action=PlannedAction.CREATE,
                specification_hash=spec_hash,
                expected_content_hash=content_hash(content),
                source=f"project:{specification.project.package_name}",
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
    def _ownership(relative_path: PurePosixPath) -> FileOwnership:
        if relative_path in {
            PurePosixPath(".gitignore"),
            PurePosixPath("README.md"),
        } or relative_path.parts[-2:] == ("application", "extensions.py"):
            return FileOwnership.SCAFFOLDED
        return FileOwnership.GENERATED

    @staticmethod
    def _render_gitignore() -> str:
        return (
            "__pycache__/\n"
            "*.py[cod]\n"
            "*.egg-info/\n"
            ".pytest_cache/\n"
            ".ruff_cache/\n"
            ".venv/\n"
            "venv/\n"
            "build/\n"
            "dist/\n"
            ".autoforge/dist/\n"
            "logs/\n"
            "*.env\n"
        )

    @staticmethod
    def _render_pyproject(
        *,
        package_name: str,
        version: str,
        description: str,
        dependencies: list[str],
        include_redis: bool,
        include_rabbitmq: bool,
        database_provider: str,
        ruff_exclude: list[str],
    ) -> str:
        redis_dependency = '    "redis>=5,<7",\n' if include_redis else ""
        rabbitmq_dependency = (
            '    "aio-pika>=9.5,<10",\n' if include_rabbitmq else ""
        )
        database_dependency = (
            '    "asyncmy>=0.2,<1",\n'
            '    "cryptography>=44,<47",\n'
            if database_provider == "mysql"
            else '    "asyncpg>=0.30,<1",\n'
        )
        project_dependencies = "".join(
            f"    {json.dumps(dependency, ensure_ascii=False)},\n"
            for dependency in dependencies
        )
        ruff_configuration = ""
        if ruff_exclude:
            ruff_configuration = (
                "[tool.ruff]\n"
                f"extend-exclude = {json.dumps(ruff_exclude, ensure_ascii=False)}\n"
                "\n"
            )
        return (
            "[build-system]\n"
            'requires = ["setuptools>=68"]\n'
            'build-backend = "setuptools.build_meta"\n'
            "\n"
            "[project]\n"
            f"name = {json.dumps(package_name, ensure_ascii=False)}\n"
            f"version = {json.dumps(version, ensure_ascii=False)}\n"
            f"description = {json.dumps(description, ensure_ascii=False)}\n"
            'requires-python = ">=3.12"\n'
            'dependencies = [\n'
            f"{rabbitmq_dependency}"
            '    "alembic>=1.18,<2",\n'
            f"{database_dependency}"
            '    "fastapi",\n'
            f"{redis_dependency}"
            '    "sqlalchemy>=2.0,<3",\n'
            '    "uvicorn",\n'
            f"{project_dependencies}"
            ']\n'
            "\n"
            "[project.optional-dependencies]\n"
            'test = ["httpx", "pytest", "ruff"]\n'
            "\n"
            "[tool.setuptools]\n"
            'package-dir = {"" = "src"}\n'
            "\n"
            "[tool.setuptools.packages.find]\n"
            'where = ["src"]\n'
            "\n"
            "[tool.pytest.ini_options]\n"
            'pythonpath = ["src"]\n'
            'testpaths = ["tests"]\n'
            "\n"
            f"{ruff_configuration}"
            "[tool.ruff.lint.isort]\n"
            f'known-first-party = ["{package_name}"]\n'
        )

    @staticmethod
    def _render_readme(
        *,
        project_name: str,
        description: str,
        package_name: str,
    ) -> str:
        summary = description or "AutoForge로 생성한 FastAPI 프로젝트"
        return (
            f"# {project_name}\n"
            "\n"
            f"{summary}\n"
            "\n"
            "## 실행\n"
            "\n"
            "```bash\n"
            'pip install -e ".[test]"\n'
            f"uvicorn {package_name}.main:app --reload\n"
            "```\n"
            "\n"
            "## 로그\n"
            "\n"
            "JSON 로그는 표준출력과 `LOG_DIRECTORY`(기본값 `logs`)에 함께 기록됩니다. "
            "컨테이너에서는 `/app/logs`를 영속 볼륨으로 마운트하세요.\n"
        )

    @staticmethod
    def _render_main(package_name: str) -> str:
        return (
            f"from {package_name}.application.app_factory import create_app\n"
            "\n"
            "app = create_app()\n"
        )

    @staticmethod
    def _render_app_factory(
        *,
        package_name: str,
        project_name: str,
        version: str,
        has_durable_jobs: bool,
    ) -> str:
        title_literal = json.dumps(project_name, ensure_ascii=False)
        version_literal = json.dumps(version, ensure_ascii=False)
        lifespan_import = (
            f"from {package_name}.application.generated.lifespan import lifespan\n"
        )
        lifespan_line = "        lifespan=lifespan,\n"
        durable_jobs_import = ""
        durable_jobs_line = ""
        if has_durable_jobs:
            durable_jobs_import = (
                f"from {package_name}.routers.durable_jobs "
                "import router as durable_jobs_router\n"
            )
            durable_jobs_line = "    app.include_router(durable_jobs_router)\n"
        return (
            "from fastapi import FastAPI\n"
            "\n"
            f"from {package_name}.application.extensions import USER_ROUTERS\n"
            f"{lifespan_import}"
            f"from {package_name}.application.generated.module_registry "
            "import MODULE_ROUTERS\n"
            f"from {package_name}.application.observability import (\n"
            "    configure_logging,\n"
            "    install_request_logging,\n"
            ")\n"
            f"{durable_jobs_import}"
            f"from {package_name}.routers.health import router as health_router\n"
            "\n"
            "\n"
            "def create_app() -> FastAPI:\n"
            "    configure_logging()\n"
            f"    app = FastAPI(\n"
            f"        title={title_literal},\n"
            f"        version={version_literal},\n"
            f"{lifespan_line}"
            f"    )\n"
            "    install_request_logging(app)\n"
            "    app.include_router(health_router)\n"
            f"{durable_jobs_line}"
            "    for router in USER_ROUTERS:\n"
            "        app.include_router(router)\n"
            "    for router in MODULE_ROUTERS:\n"
            "        app.include_router(router)\n"
            "    return app\n"
        )

    @staticmethod
    def _render_extension_routers() -> str:
        return (
            "from collections.abc import Callable\n"
            "from contextlib import AbstractAsyncContextManager\n"
            "\n"
            "from fastapi import APIRouter, FastAPI\n"
            "\n"
            "UserLifespanFactory = Callable[[FastAPI], AbstractAsyncContextManager[None]]\n"
            "\n"
            "USER_ROUTERS: tuple[APIRouter, ...] = ()\n"
            "USER_LIFESPANS: tuple[UserLifespanFactory, ...] = ()\n"
        )

    @staticmethod
    def _render_observability(package_name: str) -> str:
        logger_name = json.dumps(package_name)
        return (
            "from __future__ import annotations\n"
            "\n"
            "import json\n"
            "import logging\n"
            "import os\n"
            "import re\n"
            "import socket\n"
            "from collections.abc import Awaitable, Callable\n"
            "from datetime import UTC, datetime\n"
            "from logging.handlers import RotatingFileHandler\n"
            "from pathlib import Path\n"
            "from time import perf_counter\n"
            "from uuid import uuid4\n"
            "\n"
            "from fastapi import FastAPI, Request, Response\n"
            "\n"
            f"LOGGER_NAME = {logger_name}\n"
            "LOGGER = logging.getLogger(LOGGER_NAME)\n"
            "_MANAGED_HANDLER = '_generated_observability_handler'\n"
            "_URL_CREDENTIALS = re.compile(r'://([^:/\\s]+):([^@/\\s]+)@')\n"
            "_SECRET_VALUE = re.compile(r'(?i)\\b(password|token|secret|api[_-]?key)\\s*([=:])\\s*([^,\\s]+)')\n"
            "\n"
            "\n"
            "class JsonFormatter(logging.Formatter):\n"
            "    def format(self, record: logging.LogRecord) -> str:\n"
            "        payload: dict[str, object] = {\n"
            "            'timestamp': datetime.fromtimestamp(record.created, UTC).isoformat(),\n"
            "            'level': record.levelname,\n"
            "            'logger': record.name,\n"
            "            'message': self._redact(record.getMessage()),\n"
            "        }\n"
            "        for field_name in (\n"
            "            'request_id', 'method', 'path', 'status_code', 'duration_ms', 'event_id',\n"
            "            'event_type', 'job_type', 'job_id', 'run_key', 'attempt', 'max_attempts'\n"
            "        ):\n"
            "            value = getattr(record, field_name, None)\n"
            "            if value is not None:\n"
            "                payload[field_name] = value\n"
            "        if record.exc_info:\n"
            "            payload['exception'] = self._redact(self.formatException(record.exc_info))\n"
            "        return json.dumps(payload, ensure_ascii=False, default=str)\n"
            "\n"
            "    @staticmethod\n"
            "    def _redact(value: str) -> str:\n"
            "        value = _URL_CREDENTIALS.sub(r'://\\1:[REDACTED]@', value)\n"
            "        return _SECRET_VALUE.sub(r'\\1\\2[REDACTED]', value)\n"
            "\n"
            "\n"
            "def configure_logging() -> None:\n"
            "    LOGGER.setLevel(os.getenv('LOG_LEVEL', 'INFO').upper())\n"
            "    LOGGER.propagate = False\n"
            "    for handler in list(LOGGER.handlers):\n"
            "        if getattr(handler, _MANAGED_HANDLER, False):\n"
            "            LOGGER.removeHandler(handler)\n"
            "            handler.close()\n"
            "    directory = Path(os.getenv('LOG_DIRECTORY', 'logs'))\n"
            "    directory.mkdir(parents=True, exist_ok=True)\n"
            "    file_handler = RotatingFileHandler(\n"
            "        directory / f'{LOGGER_NAME}-{socket.gethostname()}-{os.getpid()}.log',\n"
            "        maxBytes=int(os.getenv('LOG_MAX_BYTES', str(10 * 1024 * 1024))),\n"
            "        backupCount=int(os.getenv('LOG_BACKUP_COUNT', '7')),\n"
            "        encoding='utf-8',\n"
            "    )\n"
            "    formatter = JsonFormatter()\n"
            "    for handler in (logging.StreamHandler(), file_handler):\n"
            "        handler.setFormatter(formatter)\n"
            "        setattr(handler, _MANAGED_HANDLER, True)\n"
            "        LOGGER.addHandler(handler)\n"
            "\n"
            "\n"
            "def install_request_logging(app: FastAPI) -> None:\n"
            "    @app.middleware('http')\n"
            "    async def log_request(\n"
            "        request: Request,\n"
            "        call_next: Callable[[Request], Awaitable[Response]],\n"
            "    ) -> Response:\n"
            "        started_at = perf_counter()\n"
            "        request_id = request.headers.get('X-Request-ID') or uuid4().hex\n"
            "        fields = {\n"
            "            'request_id': request_id,\n"
            "            'method': request.method,\n"
            "            'path': request.url.path,\n"
            "        }\n"
            "        try:\n"
            "            response = await call_next(request)\n"
            "        except Exception:\n"
            "            LOGGER.exception(\n"
            "                'request failed',\n"
            "                extra={\n"
            "                    **fields,\n"
            "                    'status_code': 500,\n"
            "                    'duration_ms': round((perf_counter() - started_at) * 1000, 2),\n"
            "                },\n"
            "            )\n"
            "            raise\n"
            "        response.headers['X-Request-ID'] = request_id\n"
            "        LOGGER.info(\n"
            "            'request completed',\n"
            "            extra={\n"
            "                **fields,\n"
            "                'status_code': response.status_code,\n"
            "                'duration_ms': round((perf_counter() - started_at) * 1000, 2),\n"
            "            },\n"
            "        )\n"
            "        return response\n"
        )

    @staticmethod
    def _render_module_registry(
        *,
        package_name: str,
        module_names: list[str],
    ) -> str:
        package_imports: list[str] = []
        aliases: list[str] = []
        for module_name in module_names:
            alias = f"{module_name}_router"
            aliases.append(alias)
        for module_name in sorted(module_names):
            alias = f"{module_name}_router"
            package_imports.append(
                f"from {package_name}.modules.{module_name}.generated.router "
                f"import router as {alias}"
            )

        if not aliases:
            declaration = "MODULE_ROUTERS: tuple[APIRouter, ...] = ()"
        else:
            router_items = "".join(f"    {alias},\n" for alias in aliases)
            declaration = (
                f"MODULE_ROUTERS: tuple[APIRouter, ...] = (\n{router_items})\n"
            )
        sections = ["from fastapi import APIRouter"]
        if package_imports:
            sections.append("\n".join(package_imports))
        sections.append(declaration.rstrip())
        return "\n\n".join(sections) + "\n"

    @staticmethod
    def _render_durable_jobs_router(package_name: str) -> str:
        return (
            "import os\n"
            "from datetime import datetime\n"
            "from secrets import compare_digest\n"
            "from typing import Annotated\n"
            "\n"
            "from fastapi import APIRouter, Depends, Header, HTTPException, Query, status\n"
            "from pydantic import BaseModel, Field\n"
            "\n"
            f"from {package_name}.infrastructure.database.provider import get_session_registry\n"
            f"from {package_name}.infrastructure.database.routing import ShardTarget\n"
            f"from {package_name}.infrastructure.database.session import AsyncSessionRegistry\n"
            f"from {package_name}.infrastructure.durable_jobs.contracts import (\n"
            "    JOB_DEFINITIONS,\n"
            "    DurableJobStatus,\n"
            ")\n"
            f"from {package_name}.infrastructure.durable_jobs.repository import DurableJobRepository\n"
            "\n"
            "\n"
            "class DurableJobTriggerRequest(BaseModel):\n"
            "    run_key: str = Field(min_length=1)\n"
            "    payload: dict[str, object] = Field(default_factory=dict)\n"
            "\n"
            "\n"
            "class DurableJobTriggerResponse(BaseModel):\n"
            "    job_id: str\n"
            "    created: bool\n"
            "\n"
            "\n"
            "class DurableJobStatusResponse(BaseModel):\n"
            "    job_id: str\n"
            "    job_type: str\n"
            "    run_key: str\n"
            "    status: str\n"
            "    payload: dict[str, object]\n"
            "    result: dict[str, object] | None\n"
            "    error: str | None\n"
            "    requested_at: datetime\n"
            "    updated_at: datetime\n"
            "\n"
            "\n"
            "def require_durable_job_api_token(\n"
            "    authorization: Annotated[str | None, Header()] = None,\n"
            ") -> None:\n"
            "    expected_token = os.getenv('DURABLE_JOB_API_TOKEN')\n"
            "    if not expected_token:\n"
            "        raise HTTPException(status_code=503, detail='durable job API token is not configured')\n"
            "    scheme, _, token = (authorization or '').partition(' ')\n"
            "    if scheme != 'Bearer' or not compare_digest(token, expected_token):\n"
            "        raise HTTPException(status_code=401, detail='invalid durable job API token')\n"
            "\n"
            "\n"
            "router = APIRouter(\n"
            "    prefix='/internal/jobs',\n"
            "    tags=['durable-jobs'],\n"
            "    dependencies=[Depends(require_durable_job_api_token)],\n"
            ")\n"
            "\n"
            "\n"
            "def _definition(job_type: str):\n"
            "    definition = JOB_DEFINITIONS.get(job_type)\n"
            "    if definition is None:\n"
            "        raise HTTPException(status_code=404, detail='durable job type not found')\n"
            "    return definition\n"
            "\n"
            "\n"
            "def _status_response(job) -> DurableJobStatusResponse:\n"
            "    return DurableJobStatusResponse(\n"
            "        job_id=job.job_id,\n"
            "        job_type=job.job_type,\n"
            "        run_key=job.run_key,\n"
            "        status=job.status,\n"
            "        payload=job.payload,\n"
            "        result=job.result,\n"
            "        error=job.error,\n"
            "        requested_at=job.requested_at,\n"
            "        updated_at=job.updated_at,\n"
            "    )\n"
            "\n"
            "\n"
            "@router.post(\n"
            "    '/{job_type}',\n"
            "    response_model=DurableJobTriggerResponse,\n"
            "    status_code=status.HTTP_202_ACCEPTED,\n"
            ")\n"
            "async def trigger_durable_job(\n"
            "    job_type: str,\n"
            "    request: DurableJobTriggerRequest,\n"
            "    session_registry: Annotated[\n"
            "        AsyncSessionRegistry, Depends(get_session_registry)\n"
            "    ],\n"
            ") -> DurableJobTriggerResponse:\n"
            "    definition = _definition(job_type)\n"
            "    async with session_registry.session(ShardTarget(store=definition.store)) as session:\n"
            "        result = await DurableJobRepository(session).request(\n"
            "            job_type=job_type, run_key=request.run_key, payload=request.payload\n"
            "        )\n"
            "    return DurableJobTriggerResponse(\n"
            "        job_id=result.job_id, created=result.created\n"
            "    )\n"
            "\n"
            "\n"
            "@router.get('/{job_type}', response_model=list[DurableJobStatusResponse])\n"
            "async def list_durable_jobs(\n"
            "    job_type: str,\n"
            "    session_registry: Annotated[\n"
            "        AsyncSessionRegistry, Depends(get_session_registry)\n"
            "    ],\n"
            "    limit: Annotated[int, Query(ge=1, le=100)] = 20,\n"
            ") -> list[DurableJobStatusResponse]:\n"
            "    definition = _definition(job_type)\n"
            "    async with session_registry.session(ShardTarget(store=definition.store)) as session:\n"
            "        jobs = await DurableJobRepository(session).list_recent(\n"
            "            job_type=definition.name, limit=limit\n"
            "        )\n"
            "    return [_status_response(job) for job in jobs]\n"
            "\n"
            "\n"
            "@router.get('/{job_type}/{job_id}', response_model=DurableJobStatusResponse)\n"
            "async def get_durable_job(\n"
            "    job_type: str,\n"
            "    job_id: str,\n"
            "    session_registry: Annotated[\n"
            "        AsyncSessionRegistry, Depends(get_session_registry)\n"
            "    ],\n"
            ") -> DurableJobStatusResponse:\n"
            "    definition = _definition(job_type)\n"
            "    async with session_registry.session(ShardTarget(store=definition.store)) as session:\n"
            "        job = await DurableJobRepository(session).get(job_id)\n"
            "    if job is None or job.job_type != definition.name:\n"
            "        raise HTTPException(status_code=404, detail='durable job not found')\n"
            "    return _status_response(job)\n"
            "\n"
            "\n"
            "@router.delete('/{job_type}/{job_id}', response_model=DurableJobStatusResponse)\n"
            "async def cancel_durable_job(\n"
            "    job_type: str,\n"
            "    job_id: str,\n"
            "    session_registry: Annotated[\n"
            "        AsyncSessionRegistry, Depends(get_session_registry)\n"
            "    ],\n"
            ") -> DurableJobStatusResponse:\n"
            "    definition = _definition(job_type)\n"
            "    async with session_registry.session(ShardTarget(store=definition.store)) as session:\n"
            "        repository = DurableJobRepository(session)\n"
            "        job = await repository.get(job_id)\n"
            "        if job is None or job.job_type != definition.name:\n"
            "            raise HTTPException(status_code=404, detail='durable job not found')\n"
            "        if job.status == DurableJobStatus.CANCELLED.value:\n"
            "            return _status_response(job)\n"
            "        cancelled = await repository.transition(\n"
            "            job_id=job_id, expected_status=DurableJobStatus.REQUESTED,\n"
            "            status=DurableJobStatus.CANCELLED,\n"
            "        )\n"
            "        if not cancelled:\n"
            "            job = await repository.get(job_id)\n"
            "            if job is not None and job.status == DurableJobStatus.CANCELLED.value:\n"
            "                return _status_response(job)\n"
            "            raise HTTPException(status_code=409, detail='durable job is already running or finished')\n"
            "        job = await repository.get(job_id)\n"
            "        if job is None:\n"
            "            raise HTTPException(status_code=404, detail='durable job not found')\n"
            "        return _status_response(job)\n"
        )

    @staticmethod
    def _render_health_router(
        *, package_name: str, has_database: bool, has_session_store: bool
    ) -> str:
        required_dependencies = tuple(
            name
            for name, enabled in (
                ("session_registry", has_database),
                ("session_store", has_session_store),
            )
            if enabled
        )
        readiness_third_party_imports = ""
        readiness_local_imports = ""
        readiness_errors: list[str] = []
        if has_database:
            readiness_third_party_imports += "from sqlalchemy.exc import SQLAlchemyError\n"
            readiness_errors.extend(("SQLAlchemyError", "OSError"))
        if has_session_store:
            readiness_local_imports += (
                f"from {package_name}.infrastructure.session_store.protocol import "
                "SessionStoreError\n"
            )
            readiness_errors.append("SessionStoreError")
        if not readiness_errors:
            readiness_errors.append("RuntimeError")
        readiness_error_types = ", ".join(readiness_errors)
        readiness_exception = (
            f"        except ({readiness_error_types}):\n"
            if readiness_error_types
            else ""
        )
        imports = (
            "from fastapi import APIRouter, HTTPException, Request, status\n"
            + readiness_third_party_imports
            + ("\n" if readiness_local_imports else "")
            + readiness_local_imports
            + "\n"
        )
        return (
            f"{imports}"
            'router = APIRouter(tags=["health"])\n'
            f"_REQUIRED_DEPENDENCIES = {required_dependencies!r}\n"
            "\n"
            "\n"
            '@router.get("/health")\n'
            "async def health() -> dict[str, str]:\n"
            '    return {"status": "ok"}\n'
            "\n"
            "\n"
            '@router.get("/readiness")\n'
            "async def readiness(request: Request) -> dict[str, str]:\n"
            "    for state_name in _REQUIRED_DEPENDENCIES:\n"
            "        dependency = getattr(request.app.state, state_name, None)\n"
            "        health_check = getattr(dependency, 'health_check', None)\n"
            "        if health_check is None:\n"
            "            raise HTTPException(\n"
            "                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,\n"
            "                detail=f'{state_name} is not initialized',\n"
            "            )\n"
            "        try:\n"
            "            await health_check()\n"
            f"{readiness_exception}"
            "            raise HTTPException(\n"
            "                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,\n"
            "                detail=f'{state_name} is not ready',\n"
            "            ) from None\n"
            '    return {"status": "ready"}\n'
        )

    @staticmethod
    def _render_health_test(
        package_name: str,
        redis_env_values: list[tuple[str, str]],
        database_env_names: list[str],
        database_provider: str,
        has_database: bool,
        has_session_store: bool,
    ) -> str:
        redis_env_names = [name for name, _ in redis_env_values]
        required_env_names = [*redis_env_names, *database_env_names]
        monkeypatch_argument = "monkeypatch: pytest.MonkeyPatch" if required_env_names else ""
        redis_env_setup = "".join(
            f'    monkeypatch.setenv("{name}", "{value}")\n'
            for name, value in redis_env_values
        )
        database_env_setup = "".join(
            f'    monkeypatch.setenv("{name}", '
            + (
                '"mysql+asyncmy://user:password@localhost/database?charset=utf8mb4")\n'
                if database_provider == "mysql"
                else '"postgresql+asyncpg://user:password@localhost/database")\n'
            )
            for name in database_env_names
        )
        readiness_state_names = tuple(
            state_name
            for state_name, enabled in (
                ("session_registry", has_database),
                ("session_store", has_session_store),
            )
            if enabled
        )
        readiness_state_setup = "".join(
            f"        app.state.{state_name} = ReadyDependency()\n"
            for state_name in readiness_state_names
        )
        readiness_dependency = (
            "    class ReadyDependency:\n"
            "        async def health_check(self) -> None:\n"
            "            return None\n"
            "\n"
            if readiness_state_setup
            else ""
        )
        readiness_unavailable_dependency = (
            "    class UnavailableDependency:\n"
            "        async def health_check(self) -> None:\n"
            "            raise OSError('database unavailable')\n"
            "\n"
            if has_database
            else ""
        )
        readiness_missing_state_check = (
            '        not_ready = client.get("/readiness")\n'
            if readiness_state_setup
            else ""
        )
        readiness_missing_state_setup = (
            "        app.state.session_registry = UnavailableDependency()\n"
            if has_database
            else (
                f"        app.state.{readiness_state_names[0]} = None\n"
                if readiness_state_names
                else ""
            )
        )
        readiness_missing_state_assertion = (
            "    assert not_ready.status_code == 503\n"
            if readiness_state_setup
            else ""
        )
        pytest_import = "import pytest\n" if required_env_names else ""
        return (
            f"{pytest_import}"
            "from fastapi.testclient import TestClient\n"
            "\n"
            f"from {package_name}.main import app\n"
            "\n"
            "\n"
            f"def test_health({monkeypatch_argument}) -> None:\n"
            f"{redis_env_setup}"
            f"{database_env_setup}"
            f"{readiness_dependency}"
            f"{readiness_unavailable_dependency}"
            "    with TestClient(app) as client:\n"
            '        response = client.get("/health")\n'
            f"{readiness_missing_state_setup}"
            f"{readiness_missing_state_check}"
            f"{readiness_state_setup}"
            '        readiness = client.get("/readiness")\n'
            "\n"
            "    assert response.status_code == 200\n"
            '    assert response.json() == {"status": "ok"}\n'
            f"{readiness_missing_state_assertion}"
            "    assert readiness.status_code == 200\n"
            '    assert readiness.json() == {"status": "ready"}\n'
        )

    @staticmethod
    def _render_lifespan(
        package_name: str,
        *,
        has_database: bool,
        has_session_store: bool,
        has_heartbeat_reporter: bool,
    ) -> str:
        imports = ""
        heartbeat_import = ""
        entries = ""
        if has_database:
            imports += (
                f"from {package_name}.infrastructure.database.provider import (\n"
                "    database_lifespan,\n"
                ")\n"
            )
            entries += (
                "        await stack.enter_async_context(database_lifespan(app))\n"
            )
        if has_session_store:
            imports += (
                f"from {package_name}.infrastructure.session_store.provider import (\n"
                "    session_store_lifespan,\n"
                ")\n"
            )
            entries += (
                "        await stack.enter_async_context(session_store_lifespan(app))\n"
            )
        if has_heartbeat_reporter:
            heartbeat_import = (
                f"from {package_name}.application.generated.service_heartbeat import (\n"
                "    service_heartbeat_lifespan,\n"
                ")\n"
            )
            entries += (
                "        await stack.enter_async_context(service_heartbeat_lifespan(app))\n"
            )
        return (
            "from collections.abc import AsyncIterator\n"
            "from contextlib import AsyncExitStack, asynccontextmanager\n"
            "\n"
            "from fastapi import FastAPI\n"
            "\n"
            f"from {package_name}.application import extensions\n"
            f"{heartbeat_import}"
            f"from {package_name}.application.observability import LOGGER\n"
            f"{imports}"
            "\n"
            "\n"
            "@asynccontextmanager\n"
            "async def lifespan(app: FastAPI) -> AsyncIterator[None]:\n"
            "    LOGGER.info('application starting')\n"
            "    async with AsyncExitStack() as stack:\n"
            f"{entries}"
            "        for lifespan_factory in getattr(extensions, 'USER_LIFESPANS', ()):\n"
            "            await stack.enter_async_context(lifespan_factory(app))\n"
            "        try:\n"
            "            yield\n"
            "        finally:\n"
            "            LOGGER.info('application stopping')\n"
        )

    @staticmethod
    def _render_service_heartbeat_reporter(
        *,
        package_name: str,
        service_name: str,
        deployed_version: str,
        endpoint_env: str,
        token_env: str,
        interval_seconds: int,
        dependencies: dict[str, str],
    ) -> str:
        return (
            "import asyncio\n"
            "import json\n"
            "import os\n"
            "import re\n"
            "import socket\n"
            "from collections.abc import AsyncIterator\n"
            "from contextlib import asynccontextmanager, suppress\n"
            "from urllib.request import Request, urlopen\n"
            "\n"
            "from fastapi import FastAPI\n"
            "\n"
            f"from {package_name}.application.observability import LOGGER\n"
            "\n"
            f"_ENDPOINT_ENV = {endpoint_env!r}\n"
            f"_TOKEN_ENV = {token_env!r}\n"
            f"_SERVICE_NAME = {service_name!r}\n"
            f"_DEPLOYED_VERSION = {deployed_version!r}\n"
            f"_DEPENDENCIES = {dependencies!r}\n"
            f"_INTERVAL_SECONDS = {interval_seconds}\n"
            "\n"
            "\n"
            "@asynccontextmanager\n"
            "async def service_heartbeat_lifespan(_app: FastAPI) -> AsyncIterator[None]:\n"
            "    task = asyncio.create_task(\n"
            "        run_service_heartbeat_reporter(),\n"
            "        name='service-heartbeat-reporter',\n"
            "    )\n"
            "    try:\n"
            "        yield\n"
            "    finally:\n"
            "        task.cancel()\n"
            "        with suppress(asyncio.CancelledError):\n"
            "            await task\n"
            "\n"
            "\n"
            "async def run_service_heartbeat_reporter(\n"
            "    *,\n"
            "    service_name: str = _SERVICE_NAME,\n"
            "    dependencies: dict[str, str] = _DEPENDENCIES,\n"
            ") -> None:\n"
            "    endpoint = os.getenv(_ENDPOINT_ENV)\n"
            "    token = os.getenv(_TOKEN_ENV)\n"
            "    if not endpoint or not token:\n"
            "        LOGGER.info('service heartbeat reporter disabled')\n"
            "        return\n"
            "    while True:\n"
            "        try:\n"
            "            await asyncio.to_thread(\n"
            "                _post_heartbeat, endpoint, token, service_name, dependencies\n"
            "            )\n"
            "        except (OSError, ValueError) as error:\n"
            "            LOGGER.warning(\n"
            "                'service heartbeat report failed: %s', type(error).__name__\n"
            "            )\n"
            "        await asyncio.sleep(_INTERVAL_SECONDS)\n"
            "\n"
            "\n"
            "def _post_heartbeat(\n"
            "    endpoint: str, token: str, service_name: str, dependencies: dict[str, str]\n"
            ") -> None:\n"
            "    payload = {\n"
            "        'instance_id': _instance_id(),\n"
            "        'service_name': service_name,\n"
            "        'deployed_version': _DEPLOYED_VERSION,\n"
            "        'dependencies': dependencies,\n"
            "    }\n"
            "    request = Request(\n"
            "        endpoint,\n"
            "        data=json.dumps(payload).encode(),\n"
            "        headers={\n"
            "            'Authorization': f'Bearer {token}',\n"
            "            'Content-Type': 'application/json',\n"
            "        },\n"
            "        method='POST',\n"
            "    )\n"
            "    with urlopen(request, timeout=5) as response:\n"
            "        response.read()\n"
            "\n"
            "\n"
            "def _instance_id() -> str:\n"
            "    candidate = os.getenv('POD_NAME') or os.getenv('HOSTNAME') or socket.gethostname()\n"
            "    normalized = re.sub(r'[^A-Za-z0-9._:-]', '-', candidate).strip('-')\n"
            "    return normalized[:128] or 'unknown'\n"
        )
