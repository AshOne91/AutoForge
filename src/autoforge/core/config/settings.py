from pydantic import BaseModel, ConfigDict, Field


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


class Settings(ConfigModel):
    project: ProjectConfig
    workspace: WorkspaceConfig
    logging: LoggingConfig
    plugins: PluginConfig = Field(default_factory=PluginConfig)
