from pydantic import BaseModel


class ProjectConfig(BaseModel):
    name: str
    version: str


class WorkspaceConfig(BaseModel):
    output: str


class LoggingConfig(BaseModel):
    level: str


class PluginConfig(BaseModel):
    enabled: list[str]


class Settings(BaseModel):
    project: ProjectConfig
    workspace: WorkspaceConfig
    logging: LoggingConfig
    plugins: PluginConfig