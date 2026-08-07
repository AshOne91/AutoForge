"""Generate least-privilege verification CI configuration."""

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
from autoforge.core.specification import CiProvider, CiWorkflow, ProjectSpec

CI_GENERATOR_ID: Final = "autoforge.generator.ci"
CI_GENERATOR_VERSION: Final = "0.1.0"


class CIGenerator:
    """Generate CI verification files without deployment credentials or actions."""

    @property
    def generator_id(self) -> str:
        return CI_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return CI_GENERATOR_VERSION

    def render(self, specification: ProjectSpec) -> dict[PurePosixPath, str]:
        providers = set(specification.tooling.ci.providers)
        if not providers:
            return {}
        files: dict[PurePosixPath, str] = {}
        workflows = specification.tooling.ci.workflows
        if CiProvider.GITHUB_ACTIONS in providers:
            files[PurePosixPath(".github", "workflows", "ci.yml")] = (
                self._render_github_actions(workflows)
            )
        if CiProvider.JENKINS in providers:
            files[PurePosixPath("Jenkinsfile")] = self._render_jenkins(workflows)
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
                    ownership=FileOwnership.GENERATED,
                    action=PlannedAction.CREATE,
                    specification_hash=spec_hash,
                    expected_content_hash=content_hash(content),
                    source="project:ci",
                )
                for path, content in sorted(
                    rendered.items(), key=lambda item: item[0].as_posix()
                )
            ],
        )

    @staticmethod
    def _commands(workflows: list[CiWorkflow]) -> list[str]:
        commands = [
            "python -m pip install -e '.[test]' ruff",
            "python -m ruff check .",
            "python -m pytest",
        ]
        if CiWorkflow.BUILD in workflows:
            commands.append("python -m pip wheel --no-deps --wheel-dir dist .")
        return commands

    def _render_github_actions(self, workflows: list[CiWorkflow]) -> str:
        steps = "\n".join(
            f"      - run: {command}" for command in self._commands(workflows)
        )
        return (
            "name: CI\n\n"
            "on:\n"
            "  pull_request:\n"
            "  push:\n"
            "    branches: [main]\n\n"
            "permissions:\n"
            "  contents: read\n\n"
            "jobs:\n"
            "  verify:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "      - uses: actions/setup-python@v5\n"
            "        with:\n"
            "          python-version: '3.12'\n"
            f"{steps}\n"
        )

    def _render_jenkins(self, workflows: list[CiWorkflow]) -> str:
        commands = "\n".join(
            f"        sh {command!r}" for command in self._commands(workflows)
        )
        return (
            "pipeline {\n"
            "  agent any\n"
            "  stages {\n"
            "    stage('verify') {\n"
            "      steps {\n"
            f"{commands}\n"
            "      }\n"
            "    }\n"
            "  }\n"
            "}\n"
        )
