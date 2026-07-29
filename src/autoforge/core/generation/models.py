from enum import StrEnum
from pathlib import PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def validate_relative_file_path(value: object) -> PurePosixPath:
    path = PurePosixPath(str(value))
    if path.is_absolute():
        raise ValueError("생성 파일 경로는 상대 경로여야 합니다.")
    if path.parts and ":" in path.parts[0]:
        raise ValueError("생성 파일 경로에는 드라이브를 지정할 수 없습니다.")
    if not path.parts or path == PurePosixPath("."):
        raise ValueError("생성 파일 경로는 비어 있을 수 없습니다.")
    if ".." in path.parts:
        raise ValueError("생성 파일 경로에는 '..'을 사용할 수 없습니다.")
    if "\\" in str(value):
        raise ValueError("생성 파일 경로에는 역슬래시를 사용할 수 없습니다.")
    return path


def validate_sha256(value: str) -> str:
    if len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValueError("Hash는 소문자 SHA-256 16진수 문자열이어야 합니다.")
    return value


class GenerationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class FileOwnership(StrEnum):
    GENERATED = "generated"
    SCAFFOLDED = "scaffolded"
    USER_OWNED = "user_owned"


class PlannedAction(StrEnum):
    CREATE = "create"
    REPLACE_GENERATED = "replace_generated"
    KEEP = "keep"
    SKIP = "skip"
    CONFLICT = "conflict"


class FileResultStatus(StrEnum):
    CREATED = "created"
    CHANGED = "changed"
    UNCHANGED = "unchanged"
    PRESERVED = "preserved"
    SKIPPED = "skipped"
    CONFLICT = "conflict"
    FAILED = "failed"


class PlannedFile(GenerationModel):
    relative_path: PurePosixPath
    generator_id: str = Field(min_length=1)
    generator_version: str = Field(min_length=1)
    ownership: FileOwnership
    action: PlannedAction
    specification_hash: str
    expected_content_hash: str
    source: str = Field(min_length=1)

    @field_validator("relative_path", mode="before")
    @classmethod
    def validate_relative_path(cls, value: object) -> PurePosixPath:
        return validate_relative_file_path(value)

    @field_validator("specification_hash", "expected_content_hash")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        return validate_sha256(value)

    @model_validator(mode="after")
    def validate_ownership_action(self) -> "PlannedFile":
        if (
            self.ownership is FileOwnership.USER_OWNED
            and self.action
            not in {PlannedAction.KEEP, PlannedAction.SKIP, PlannedAction.CONFLICT}
        ):
            raise ValueError("USER_OWNED 파일은 생성하거나 교체할 수 없습니다.")
        if (
            self.action is PlannedAction.REPLACE_GENERATED
            and self.ownership is not FileOwnership.GENERATED
        ):
            raise ValueError("GENERATED 파일만 교체할 수 있습니다.")
        return self


class GenerationPlan(GenerationModel):
    specification_version: str = Field(min_length=1)
    specification_hash: str
    files: list[PlannedFile] = Field(default_factory=list)

    @field_validator("specification_hash")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        return validate_sha256(value)

    @model_validator(mode="after")
    def validate_unique_paths(self) -> "GenerationPlan":
        paths = [file.relative_path for file in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError("GenerationPlan의 파일 경로는 중복될 수 없습니다.")
        return self


class ManifestFile(GenerationModel):
    relative_path: PurePosixPath
    generator_id: str = Field(min_length=1)
    generator_version: str = Field(min_length=1)
    ownership: FileOwnership
    status: FileResultStatus
    specification_hash: str
    previous_content_hash: str | None = None
    content_hash: str | None = None
    source: str = Field(min_length=1)
    error: str | None = None

    _validate_relative_path = field_validator("relative_path", mode="before")(
        validate_relative_file_path
    )
    _validate_hash = field_validator(
        "specification_hash",
        "previous_content_hash",
        "content_hash",
    )(lambda value: value if value is None else validate_sha256(value))

    @model_validator(mode="after")
    def validate_result(self) -> "ManifestFile":
        if self.status is FileResultStatus.FAILED and self.error is None:
            raise ValueError("실패한 파일 결과에는 error가 필요합니다.")
        if self.status is not FileResultStatus.FAILED and self.error is not None:
            raise ValueError("실패하지 않은 파일 결과에는 error를 지정할 수 없습니다.")
        return self


class GenerationManifest(GenerationModel):
    job_id: str = Field(min_length=1)
    specification_version: str = Field(min_length=1)
    specification_hash: str
    files: list[ManifestFile] = Field(default_factory=list)

    @field_validator("specification_hash")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        return validate_sha256(value)

    @model_validator(mode="after")
    def validate_unique_paths(self) -> "GenerationManifest":
        paths = [file.relative_path for file in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError("GenerationManifest의 파일 경로는 중복될 수 없습니다.")
        return self
