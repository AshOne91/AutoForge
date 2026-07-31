from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from autoforge.core.specification.naming import (
    validate_class_name,
    validate_http_path,
    validate_python_name,
    validate_semantic_version,
)
from autoforge.core.specification.types import FieldType, FieldTypeKind


class StrictSpecModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class HttpMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class ProjectInfo(StrictSpecModel):
    name: str = Field(min_length=1, max_length=100)
    package_name: str
    version: str
    description: str = ""

    @field_validator("package_name")
    @classmethod
    def validate_package_name(cls, value: str) -> str:
        return validate_python_name(value)

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        return validate_semantic_version(value)


class ApplicationSpec(StrictSpecModel):
    framework: Literal["fastapi"] = "fastapi"
    modules: list[str] = Field(default_factory=list)

    @field_validator("modules")
    @classmethod
    def validate_modules(cls, values: list[str]) -> list[str]:
        validated = [validate_python_name(value) for value in values]
        if len(validated) != len(set(validated)):
            raise ValueError("Application Module 이름은 중복될 수 없습니다.")
        return validated


class ProjectSpec(StrictSpecModel):
    spec_version: Literal["1"]
    project: ProjectInfo
    application: ApplicationSpec


class ModuleInfo(StrictSpecModel):
    name: str
    display_name: str = Field(min_length=1, max_length=100)
    route_prefix: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return validate_python_name(value)

    @field_validator("route_prefix")
    @classmethod
    def validate_route_prefix(cls, value: str) -> str:
        return validate_http_path(value)


class FieldSpec(StrictSpecModel):
    name: str
    type: FieldType
    default: object | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return validate_python_name(value)


class ModelSpec(StrictSpecModel):
    name: str
    fields: list[FieldSpec] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return validate_class_name(value)

    @model_validator(mode="after")
    def validate_unique_fields(self) -> ModelSpec:
        names = [field.name for field in self.fields]
        if len(names) != len(set(names)):
            raise ValueError(f"Model '{self.name}'의 Field 이름은 중복될 수 없습니다.")
        return self


class ColumnSpec(StrictSpecModel):
    name: str
    type: FieldType
    primary_key: bool = False
    nullable: bool = False
    default: object | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return validate_python_name(value)

    @model_validator(mode="after")
    def validate_column(self) -> ColumnSpec:
        unsupported_kinds = {
            FieldTypeKind.LIST,
            FieldTypeKind.MODEL,
            FieldTypeKind.OPTIONAL,
        }
        if self.type.kind in unsupported_kinds:
            raise ValueError(
                "Database Column은 list, model 또는 optional Type을 "
                "직접 사용할 수 없습니다."
            )
        if self.primary_key and self.nullable:
            raise ValueError("Primary Key Column은 nullable일 수 없습니다.")
        return self


class TableSpec(StrictSpecModel):
    name: str
    columns: list[ColumnSpec] = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return validate_python_name(value)

    @model_validator(mode="after")
    def validate_columns(self) -> TableSpec:
        names = [column.name for column in self.columns]
        if len(names) != len(set(names)):
            raise ValueError(f"Table '{self.name}'의 Column 이름은 중복될 수 없습니다.")
        if not any(column.primary_key for column in self.columns):
            raise ValueError(f"Table '{self.name}'에는 Primary Key가 필요합니다.")
        return self


class RepositorySpec(StrictSpecModel):
    name: str
    aggregate: str
    table: str
    operations: list[str] = Field(min_length=1)

    @field_validator("name", "aggregate")
    @classmethod
    def validate_class_names(cls, value: str) -> str:
        return validate_class_name(value)

    @field_validator("table")
    @classmethod
    def validate_table_name(cls, value: str) -> str:
        return validate_python_name(value)

    @field_validator("operations")
    @classmethod
    def validate_operations(cls, values: list[str]) -> list[str]:
        validated = [validate_python_name(value) for value in values]
        if len(validated) != len(set(validated)):
            raise ValueError("Repository Operation 이름은 중복될 수 없습니다.")
        return validated


class DataPlacementMode(StrEnum):
    GLOBAL = "global"
    SHARDED = "sharded"


class DataPlacementSpec(StrictSpecModel):
    table: str
    store: str
    mode: DataPlacementMode = DataPlacementMode.GLOBAL
    partition_key: str | None = None
    unresolved_policy: Literal["error"] = "error"

    @field_validator("table", "store")
    @classmethod
    def validate_names(cls, value: str) -> str:
        return validate_python_name(value)

    @field_validator("partition_key")
    @classmethod
    def validate_partition_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_python_name(value)

    @model_validator(mode="after")
    def validate_routing(self) -> DataPlacementSpec:
        if (
            self.mode is DataPlacementMode.SHARDED
            and self.partition_key is None
        ):
            raise ValueError("Sharded Data Placement에는 partition_key가 필요합니다.")
        return self


class DatabaseSpec(StrictSpecModel):
    provider: Literal["agnostic"] = "agnostic"
    tables: list[TableSpec] = Field(default_factory=list)
    repositories: list[RepositorySpec] = Field(default_factory=list)
    placements: list[DataPlacementSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_database(self) -> DatabaseSpec:
        self._validate_unique_names(
            [table.name for table in self.tables],
            "Database Table",
        )
        self._validate_unique_names(
            [repository.name for repository in self.repositories],
            "Repository",
        )
        self._validate_unique_names(
            [placement.table for placement in self.placements],
            "Data Placement Table",
        )

        tables = {table.name: table for table in self.tables}
        for repository in self.repositories:
            if repository.table not in tables:
                raise ValueError(
                    f"Repository '{repository.name}'이 참조하는 Table이 없습니다: "
                    f"{repository.table}"
                )

        for placement in self.placements:
            table = tables.get(placement.table)
            if table is None:
                raise ValueError(
                    f"Data Placement가 참조하는 Table이 없습니다: {placement.table}"
                )
            column_names = {column.name for column in table.columns}
            if (
                placement.partition_key is not None
                and placement.partition_key not in column_names
            ):
                raise ValueError(
                    f"Table '{placement.table}'에 partition_key Column이 없습니다: "
                    f"{placement.partition_key}"
                )
        return self

    @staticmethod
    def _validate_unique_names(names: list[str], label: str) -> None:
        if len(names) != len(set(names)):
            raise ValueError(f"{label} 이름은 중복될 수 없습니다.")


class SchemaSpec(StrictSpecModel):
    fields: list[FieldSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_fields(self) -> SchemaSpec:
        names = [field.name for field in self.fields]
        if len(names) != len(set(names)):
            raise ValueError("Schema Field 이름은 중복될 수 없습니다.")
        return self


class ResponseSpec(SchemaSpec):
    model_name: str | None = Field(default=None, alias="model")

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_class_name(value)

    @model_validator(mode="after")
    def validate_response_shape(self) -> ResponseSpec:
        if self.model_name is not None and self.fields:
            raise ValueError("Response에는 model과 fields를 동시에 지정할 수 없습니다.")
        return self


class EndpointSpec(StrictSpecModel):
    name: str
    method: HttpMethod
    path: str
    request: SchemaSpec | None = None
    response: ResponseSpec
    handler: str

    @field_validator("name", "handler")
    @classmethod
    def validate_python_names(cls, value: str) -> str:
        return validate_python_name(value)

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return validate_http_path(value)


class ModuleSpec(StrictSpecModel):
    spec_version: Literal["1"]
    module: ModuleInfo
    models: list[ModelSpec] = Field(default_factory=list)
    endpoints: list[EndpointSpec] = Field(default_factory=list)
    database: DatabaseSpec | None = None

    @model_validator(mode="after")
    def validate_module(self) -> ModuleSpec:
        model_names = [model.name for model in self.models]
        if len(model_names) != len(set(model_names)):
            raise ValueError("Module Model 이름은 중복될 수 없습니다.")

        endpoint_names = [endpoint.name for endpoint in self.endpoints]
        if len(endpoint_names) != len(set(endpoint_names)):
            raise ValueError("Module Endpoint 이름은 중복될 수 없습니다.")

        known_models = set(model_names)
        if self.database is not None:
            for repository in self.database.repositories:
                if repository.aggregate not in known_models:
                    raise ValueError(
                        f"Repository '{repository.name}'이 참조하는 Aggregate "
                        f"Model이 없습니다: {repository.aggregate}"
                    )
        for model in self.models:
            for field in model.fields:
                self._validate_type_references(field.type, known_models)

        for endpoint in self.endpoints:
            if endpoint.request is not None:
                for field in endpoint.request.fields:
                    self._validate_type_references(field.type, known_models)
            for field in endpoint.response.fields:
                self._validate_type_references(field.type, known_models)
            if (
                endpoint.response.model_name is not None
                and endpoint.response.model_name not in known_models
            ):
                raise ValueError(
                    f"정의되지 않은 Response Model입니다: "
                    f"{endpoint.response.model_name}"
                )
        return self

    @classmethod
    def _validate_type_references(
        cls,
        field_type: FieldType,
        known_models: set[str],
    ) -> None:
        if (
            field_type.kind is FieldTypeKind.MODEL
            and field_type.reference not in known_models
        ):
            raise ValueError(f"정의되지 않은 Model 참조입니다: {field_type.reference}")
        if field_type.item is not None:
            cls._validate_type_references(field_type.item, known_models)
