from dataclasses import dataclass

from autoforge.core.event import Event


@dataclass(frozen=True, kw_only=True, slots=True)
class GenerationJobCreatedEvent(Event):
    unit_ids: tuple[str, ...]


@dataclass(frozen=True, kw_only=True, slots=True)
class GenerationJobPlannedEvent(Event):
    unit_ids: tuple[str, ...]


@dataclass(frozen=True, kw_only=True, slots=True)
class GenerationStartedEvent(Event):
    unit_count: int


@dataclass(frozen=True, kw_only=True, slots=True)
class GenerationCompletedEvent(Event):
    unit_count: int
    manifest_path: str


@dataclass(frozen=True, kw_only=True, slots=True)
class GenerationFailedEvent(Event):
    error_type: str


@dataclass(frozen=True, kw_only=True, slots=True)
class ValidationStartedEvent(Event):
    step_count: int


@dataclass(frozen=True, kw_only=True, slots=True)
class ValidationCompletedEvent(Event):
    completed_steps: tuple[str, ...]


@dataclass(frozen=True, kw_only=True, slots=True)
class ValidationFailedEvent(Event):
    failed_step: str
    error_type: str


@dataclass(frozen=True, kw_only=True, slots=True)
class GitCommitStartedEvent(Event):
    branch_name: str
    allowed_path_count: int


@dataclass(frozen=True, kw_only=True, slots=True)
class GitCommitCompletedEvent(Event):
    commit_sha: str
    branch_name: str | None
    changed_paths: tuple[str, ...]
    commit_created: bool


@dataclass(frozen=True, kw_only=True, slots=True)
class GitCommitFailedEvent(Event):
    error_type: str
