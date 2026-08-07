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
        return self


class Settings(ConfigModel):
    project: ProjectConfig
    workspace: WorkspaceConfig
    logging: LoggingConfig
    plugins: PluginConfig = Field(default_factory=PluginConfig)
    git_automation: GitAutomationConfig = Field(default_factory=GitAutomationConfig)
