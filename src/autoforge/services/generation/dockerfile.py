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

GENERATOR_ID: Final = "autoforge.generator.dockerfile"
GENERATOR_VERSION: Final = "0.1.0"
DOCKERFILE_GENERATOR_ID: Final = GENERATOR_ID
DOCKERFILE_GENERATOR_VERSION: Final = GENERATOR_VERSION


class DockerfileGenerator:
    @property
    def generator_id(self) -> str:
        return GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return GENERATOR_VERSION

    def render(self, specification: ProjectSpec) -> dict[PurePosixPath, str]:
        if not specification.tooling.docker.enabled:
            return {}
        return {
            PurePosixPath("Dockerfile"): self._render_dockerfile(
                specification.project.package_name,
            )
        }

    def plan(self, specification: ProjectSpec) -> GenerationPlan:
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
    def _render_dockerfile(package_name: str) -> str:
        return (
            "FROM python:3.12-slim\n"
            "\n"
            "WORKDIR /app\n"
            "\n"
            "COPY pyproject.toml README.md ./\n"
            "COPY src ./src\n"
            "\n"
            'RUN pip install --no-cache-dir ".[test]"\n'
            "\n"
            'EXPOSE 8000\n'
            "\n"
            "CMD ["
            f'"uvicorn", "{package_name}.main:app", '
            '"--host", "0.0.0.0", "--port", "8000"]\n'
        )
