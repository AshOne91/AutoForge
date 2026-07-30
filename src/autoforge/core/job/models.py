from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from autoforge.core.generation import GenerationManifest
from autoforge.core.generation.models import validate_sha256


class JobModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class GenerationUnitKind(StrEnum):
    PROJECT = "project"
    MODULE = "module"


class GenerationJobStatus(StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    VALIDATING = "validating"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class GenerationUnit(JobModel):
    unit_id: str = Field(min_length=1)
    kind: GenerationUnitKind
    specification_version: str = Field(min_length=1)
    specification_hash: str

    @model_validator(mode="after")
    def validate_hash(self) -> "GenerationUnit":
        validate_sha256(self.specification_hash)
        return self


class GenerationUnitManifest(JobModel):
    unit_id: str = Field(min_length=1)
    kind: GenerationUnitKind
    manifest: GenerationManifest


class GenerationJobManifest(JobModel):
    format_version: Literal["1"] = "1"
    job_id: str = Field(min_length=1)
    units: list[GenerationUnitManifest] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_units(self) -> "GenerationJobManifest":
        unit_ids = [unit.unit_id for unit in self.units]
        if len(unit_ids) != len(set(unit_ids)):
            raise ValueError("GenerationJobManifest의 unit_id는 중복될 수 없습니다.")

        paths = []
        for unit in self.units:
            if unit.manifest.job_id != self.job_id:
                raise ValueError(
                    "하위 GenerationManifest의 job_id가 일치하지 않습니다."
                )
            paths.extend(file.relative_path for file in unit.manifest.files)
        if len(paths) != len(set(paths)):
            raise ValueError("GenerationJobManifest의 파일 경로는 중복될 수 없습니다.")
        return self


class GenerationJob(JobModel):
    job_id: str = Field(min_length=1)
    status: GenerationJobStatus = GenerationJobStatus.PENDING
    units: list[GenerationUnit] = Field(min_length=1)
    manifest: GenerationJobManifest | None = None
    error: str | None = None

    @model_validator(mode="after")
    def validate_job(self) -> "GenerationJob":
        unit_ids = [unit.unit_id for unit in self.units]
        if len(unit_ids) != len(set(unit_ids)):
            raise ValueError("GenerationJob의 unit_id는 중복될 수 없습니다.")
        if self.manifest is not None:
            if self.manifest.job_id != self.job_id:
                raise ValueError("GenerationJob과 Manifest의 job_id가 다릅니다.")
            expected_by_identity = {
                (unit.unit_id, unit.kind): unit for unit in self.units
            }
            result_units = {(unit.unit_id, unit.kind) for unit in self.manifest.units}
            if not result_units.issubset(expected_by_identity):
                raise ValueError("Manifest에 정의되지 않은 GenerationUnit이 있습니다.")
            for result in self.manifest.units:
                expected = expected_by_identity[(result.unit_id, result.kind)]
                if (
                    result.manifest.specification_version
                    != expected.specification_version
                    or result.manifest.specification_hash != expected.specification_hash
                ):
                    raise ValueError(
                        "GenerationUnit과 Manifest의 Specification이 다릅니다."
                    )
        if self.status is GenerationJobStatus.SUCCEEDED:
            if self.manifest is None:
                raise ValueError("성공한 GenerationJob에는 Manifest가 필요합니다.")
            if len(self.manifest.units) != len(self.units):
                raise ValueError(
                    "성공한 GenerationJob에는 모든 Unit 결과가 필요합니다."
                )
        if self.status is GenerationJobStatus.FAILED and self.error is None:
            raise ValueError("실패한 GenerationJob에는 error가 필요합니다.")
        if self.status is not GenerationJobStatus.FAILED and self.error is not None:
            raise ValueError(
                "실패하지 않은 GenerationJob에는 error를 지정할 수 없습니다."
            )
        return self
