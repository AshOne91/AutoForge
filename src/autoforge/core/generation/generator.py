from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import Protocol, runtime_checkable

from autoforge.core.generation.models import GenerationPlan


@runtime_checkable
class Generator[SpecificationT](Protocol):
    @property
    def generator_id(self) -> str:
        ...

    @property
    def generator_version(self) -> str:
        ...

    def render(
        self,
        specification: SpecificationT,
    ) -> Mapping[PurePosixPath, str]:
        ...

    def plan(self, specification: SpecificationT) -> GenerationPlan:
        ...
