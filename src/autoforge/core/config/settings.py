from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectConfig(ConfigModel):
    name: str
    version: str


class WorkspaceConfig(ConfigModel):
    output: str


class LoggingConfig(ConfigModel):
    level: str


class PluginConfig(ConfigModel):
    enabled: list[str] = Field(default_factory=list)


class GitAutomationConfig(ConfigModel):
    enabled: bool = False
    secret_names: dict[str, str] = Field(default_factory=dict)
    allowed_repository_hosts: frozenset[str] = frozenset({"github.com"})
    branch_prefix: str = Field(default="autoforge", min_length=1)
    protected_branches: frozenset[str] = frozenset({"main", "master"})
    author_name: str = Field(default="AutoForge", min_length=1, max_length=254)
    author_email: str = Field(
        default="autoforge@localhost", min_length=3, max_length=254
    )
    commit_message: str = Field(
        default="chore: apply AutoForge generation", min_length=1, max_length=998
    )
    signing_key: str | None = Field(default=None, min_length=1)
    git_command_timeout_seconds: float = Field(default=60.0, gt=0)
    github_api_timeout_seconds: float = Field(default=10.0, gt=0)
    push_remote_name: str = Field(default="origin", min_length=1)
    pull_request_base_branch: str = Field(default="main", min_length=1)
    pull_request_title: str = Field(
        default="chore: apply AutoForge generation", min_length=1, max_length=256
    )
    pull_request_body: str = Field(
        default="Generated and validated by AutoForge.", max_length=65_536
    )

    @model_validator(mode="after")
    def validate_enabled_configuration(self) -> "GitAutomationConfig":
        if self.enabled and not self.secret_names:
            raise ValueError(
                "Enabled Git automation requires at least one secret mapping"
            )
        if not self.allowed_repository_hosts or any(
            not host
            or host != host.strip().lower()
            or "://" in host
            or "/" in host
            for host in self.allowed_repository_hosts
        ):
            raise ValueError("Git automation repository hosts are invalid")
        if (
            self.branch_prefix != self.branch_prefix.strip()
            or self.branch_prefix.startswith(("-", "/"))
            or self.branch_prefix.endswith("/")
        ):
            raise ValueError("Git automation branch prefix is invalid")
        if not self.protected_branches or any(
            not branch or branch != branch.strip()
            for branch in self.protected_branches
        ):
            raise ValueError("Git automation protected branches are invalid")
        if self.pull_request_base_branch not in self.protected_branches:
            raise ValueError(
                "Pull Request base branch must be a protected branch"
            )
        for field_name, value in (
            ("author_name", self.author_name),
            ("author_email", self.author_email),
            ("commit_message", self.commit_message),
            ("push_remote_name", self.push_remote_name),
            ("pull_request_title", self.pull_request_title),
        ):
            if value != value.strip():
                raise ValueError(f"Git automation {field_name} is invalid")
        return self


class Settings(ConfigModel):
    project: ProjectConfig
    workspace: WorkspaceConfig
    logging: LoggingConfig
    plugins: PluginConfig = Field(default_factory=PluginConfig)
    git_automation: GitAutomationConfig = Field(default_factory=GitAutomationConfig)
