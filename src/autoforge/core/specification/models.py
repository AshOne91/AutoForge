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

    @model_validator(mode="after")
    def validate_module(self) -> ModuleSpec:
        model_names = [model.name for model in self.models]
        if len(model_names) != len(set(model_names)):
            raise ValueError("Module Model 이름은 중복될 수 없습니다.")

        endpoint_names = [endpoint.name for endpoint in self.endpoints]
        if len(endpoint_names) != len(set(endpoint_names)):
            raise ValueError("Module Endpoint 이름은 중복될 수 없습니다.")

        known_models = set(model_names)
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
