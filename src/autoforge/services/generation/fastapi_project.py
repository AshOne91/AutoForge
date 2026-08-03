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
from autoforge.core.specification import ProjectSpec

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
        has_lifespan = bool(session_services)

        rendered = {
            PurePosixPath("pyproject.toml"): self._render_pyproject(
                package_name=package_name,
                version=project.version,
                description=project.description,
                include_redis=any(
                    service.kind == "redis_session"
                    for service in specification.application.services
                ),
            ),
            PurePosixPath("README.md"): self._render_readme(
                project_name=project.name,
                description=project.description,
                package_name=package_name,
            ),
            package_root / "__init__.py": (f'__version__ = "{project.version}"\n'),
            package_root / "modules" / "__init__.py": "",
            package_root / "main.py": self._render_main(package_name),
            package_root / "application" / "__init__.py": "",
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
                has_lifespan=has_lifespan,
            ),
            package_root / "routers" / "__init__.py": "",
            package_root / "routers" / "health.py": self._render_health_router(),
            PurePosixPath("tests", "test_health.py"): self._render_health_test(
                package_name,
                required_env_names=[
                    service.url_env for service in session_services
                ],
            ),
        }
        if has_lifespan:
            rendered[
                package_root / "application" / "generated" / "lifespan.py"
            ] = self._render_lifespan(package_name)
        return rendered

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
        if relative_path == PurePosixPath("README.md"):
            return FileOwnership.SCAFFOLDED
        return FileOwnership.GENERATED

    @staticmethod
    def _render_pyproject(
        *,
        package_name: str,
        version: str,
        description: str,
        include_redis: bool,
    ) -> str:
        redis_dependency = '    "redis>=5,<7",\n' if include_redis else ""
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
            '    "alembic>=1.18,<2",\n'
            '    "asyncpg>=0.30,<1",\n'
            '    "fastapi",\n'
            f"{redis_dependency}"
            '    "sqlalchemy>=2.0,<3",\n'
            '    "uvicorn",\n'
            ']\n'
            "\n"
            "[project.optional-dependencies]\n"
            'test = ["httpx2", "pytest"]\n'
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
        has_lifespan: bool,
    ) -> str:
        title_literal = json.dumps(project_name, ensure_ascii=False)
        version_literal = json.dumps(version, ensure_ascii=False)
        lifespan_import = ""
        lifespan_argument = ""
        if has_lifespan:
            lifespan_import = (
                f"from {package_name}.application.generated.lifespan "
                "import lifespan\n"
            )
            lifespan_argument = ", lifespan=lifespan"
        return (
            "from fastapi import FastAPI\n"
            "\n"
            f"from {package_name}.application.generated.module_registry "
            "import MODULE_ROUTERS\n"
            f"{lifespan_import}"
            f"from {package_name}.routers.health import router as health_router\n"
            "\n"
            "\n"
            "def create_app() -> FastAPI:\n"
            f"    app = FastAPI(\n"
            f"        title={title_literal},\n"
            f"        version={version_literal}{lifespan_argument},\n"
            f"    )\n"
            "    app.include_router(health_router)\n"
            "    for router in MODULE_ROUTERS:\n"
            "        app.include_router(router)\n"
            "    return app\n"
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
    def _render_health_router() -> str:
        return (
            "from fastapi import APIRouter\n"
            "\n"
            'router = APIRouter(tags=["health"])\n'
            "\n"
            "\n"
            '@router.get("/health")\n'
            "async def health() -> dict[str, str]:\n"
            '    return {"status": "ok"}\n'
        )

    @staticmethod
    def _render_health_test(
        package_name: str,
        required_env_names: list[str],
    ) -> str:
        monkeypatch_argument = "monkeypatch: pytest.MonkeyPatch" if required_env_names else ""
        env_setup = "".join(
            f'    monkeypatch.setenv("{name}", "redis://localhost:6379/0")\n'
            for name in required_env_names
        )
        pytest_import = "import pytest\n\n" if required_env_names else ""
        return (
            f"{pytest_import}"
            "from fastapi.testclient import TestClient\n"
            "\n"
            f"from {package_name}.main import app\n"
            "\n"
            "\n"
            f"def test_health({monkeypatch_argument}) -> None:\n"
            f"{env_setup}"
            "    with TestClient(app) as client:\n"
            '        response = client.get("/health")\n'
            "\n"
            "    assert response.status_code == 200\n"
            '    assert response.json() == {"status": "ok"}\n'
        )

    @staticmethod
    def _render_lifespan(package_name: str) -> str:
        return (
            "from collections.abc import AsyncIterator\n"
            "from contextlib import AsyncExitStack, asynccontextmanager\n"
            "\n"
            "from fastapi import FastAPI\n"
            "\n"
            f"from {package_name}.infrastructure.session_store.provider "
            "import session_store_lifespan\n"
            "\n"
            "\n"
            "@asynccontextmanager\n"
            "async def lifespan(app: FastAPI) -> AsyncIterator[None]:\n"
            "    async with AsyncExitStack() as stack:\n"
            "        await stack.enter_async_context(session_store_lifespan(app))\n"
            "        yield\n"
        )
