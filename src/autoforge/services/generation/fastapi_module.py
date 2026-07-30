import json
from pathlib import PurePosixPath
from typing import Final

from autoforge.core.generation import (
    FileOwnership,
    GenerationPlan,
    PlannedAction,
    PlannedFile,
    content_hash,
    specification_hash,
)
from autoforge.core.specification import (
    EndpointSpec,
    FieldSpec,
    FieldTypeKind,
    ModuleSpec,
)
from autoforge.core.specification.naming import validate_python_name
from autoforge.services.generation.pydantic_types import PydanticTypeRenderer

MODULE_GENERATOR_ID: Final = "autoforge.generator.fastapi.module"
MODULE_GENERATOR_VERSION: Final = "0.1.0"


class FastAPIModuleGenerator:
    """ModuleSpec의 Pydantic Model과 HTTP Schema를 생성한다."""

    def __init__(
        self,
        package_name: str,
        type_renderer: PydanticTypeRenderer | None = None,
    ) -> None:
        self._package_name = validate_python_name(package_name)
        self._type_renderer = type_renderer or PydanticTypeRenderer()

    @property
    def generator_id(self) -> str:
        return MODULE_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return MODULE_GENERATOR_VERSION

    def render(self, specification: ModuleSpec) -> dict[PurePosixPath, str]:
        module_root = PurePosixPath(
            "src",
            self._package_name,
            "modules",
            specification.module.name,
        )
        generated_root = module_root / "generated"
        return {
            module_root / "__init__.py": "",
            module_root / "handlers.py": self._render_handlers(specification),
            generated_root / "__init__.py": "",
            generated_root / "models.py": self._render_models(specification),
            generated_root / "router.py": self._render_router(specification),
            generated_root / "schemas.py": self._render_schemas(specification),
        }

    def plan(self, specification: ModuleSpec) -> GenerationPlan:
        rendered_files = self.render(specification)
        spec_hash = specification_hash(specification)
        files = [
            PlannedFile(
                relative_path=relative_path,
                generator_id=self.generator_id,
                generator_version=self.generator_version,
                ownership=self._ownership(relative_path),
                action=PlannedAction.CREATE,
                specification_hash=spec_hash,
                expected_content_hash=content_hash(content),
                source=f"module:{specification.module.name}",
            )
            for relative_path, content in sorted(
                rendered_files.items(),
                key=lambda item: item[0].as_posix(),
            )
        ]
        return GenerationPlan(
            specification_version=specification.spec_version,
            specification_hash=spec_hash,
            files=files,
        )

    @staticmethod
    def _ownership(relative_path: PurePosixPath) -> FileOwnership:
        if relative_path.name == "handlers.py":
            return FileOwnership.SCAFFOLDED
        return FileOwnership.GENERATED

    def _render_models(self, specification: ModuleSpec) -> str:
        if not specification.models:
            return ""

        fields = [field for model in specification.models for field in model.fields]
        standard_imports = self._type_renderer.imports_for(
            [field.type for field in fields]
        )
        imports = ["from __future__ import annotations", ""]
        imports.extend(standard_imports)
        if standard_imports:
            imports.append("")
        imports.append("from pydantic import BaseModel")
        classes = [
            self._render_class(model.name, model.fields)
            for model in specification.models
        ]
        return self._join_sections(imports, classes)

    def _render_schemas(self, specification: ModuleSpec) -> str:
        schema_classes: list[str] = []
        fields: list[FieldSpec] = []
        for endpoint in specification.endpoints:
            if endpoint.request is not None:
                fields.extend(endpoint.request.fields)
                schema_classes.append(
                    self._render_class(
                        f"{self._class_prefix(endpoint)}Request",
                        endpoint.request.fields,
                    )
                )
            if endpoint.response.model_name is None:
                fields.extend(endpoint.response.fields)
                schema_classes.append(
                    self._render_class(
                        f"{self._class_prefix(endpoint)}Response",
                        endpoint.response.fields,
                    )
                )

        if not schema_classes:
            return ""

        field_types = [field.type for field in fields]
        standard_imports = self._type_renderer.imports_for(field_types)
        imports = ["from __future__ import annotations", ""]
        imports.extend(standard_imports)
        if standard_imports:
            imports.append("")
        imports.append("from pydantic import BaseModel")
        model_references = self._type_renderer.model_references(field_types)
        if model_references:
            module_name = specification.module.name
            imports.append("")
            imports.append(
                f"from {self._package_name}.modules.{module_name}.generated.models "
                f"import {', '.join(model_references)}"
            )
        return self._join_sections(imports, schema_classes)

    def _render_router(self, specification: ModuleSpec) -> str:
        module_name = specification.module.name
        module_path = f"{self._package_name}.modules.{module_name}"
        imports = [
            "from fastapi import APIRouter",
            "",
            f"from {module_path} import handlers",
        ]
        model_names = sorted(
            {
                endpoint.response.model_name
                for endpoint in specification.endpoints
                if endpoint.response.model_name is not None
            }
        )
        if model_names:
            imports.append(
                f"from {module_path}.generated.models import {', '.join(model_names)}"
            )
        schema_names = sorted(
            {
                schema_name
                for endpoint in specification.endpoints
                for schema_name in self._endpoint_schema_names(endpoint)
            }
        )
        if schema_names:
            imports.append(
                f"from {module_path}.generated.schemas import {', '.join(schema_names)}"
            )

        prefix = json.dumps(
            specification.module.route_prefix,
            ensure_ascii=False,
        )
        tag = json.dumps(
            specification.module.display_name,
            ensure_ascii=False,
        )
        router_declaration = f"router = APIRouter(prefix={prefix}, tags=[{tag}])"
        endpoints = [
            self._render_router_endpoint(endpoint)
            for endpoint in specification.endpoints
        ]
        return self._join_sections(
            imports,
            [router_declaration, *endpoints],
        )

    def _render_router_endpoint(self, endpoint: EndpointSpec) -> str:
        response_type = self._response_type(endpoint)
        method = endpoint.method.value.lower()
        path = json.dumps(endpoint.path, ensure_ascii=False)
        lines = [
            f"@router.{method}({path}, response_model={response_type})",
        ]
        if endpoint.request is None:
            lines.extend(
                [
                    f"async def {endpoint.name}() -> {response_type}:",
                    f"    return await handlers.{endpoint.handler}()",
                ]
            )
        else:
            request_type = self._request_type(endpoint)
            lines.extend(
                [
                    f"async def {endpoint.name}(",
                    f"    request: {request_type},",
                    f") -> {response_type}:",
                    f"    return await handlers.{endpoint.handler}(request)",
                ]
            )
        return "\n".join(lines)

    def _render_handlers(self, specification: ModuleSpec) -> str:
        if not specification.endpoints:
            return ""

        module_name = specification.module.name
        module_path = f"{self._package_name}.modules.{module_name}.generated"
        imports = ["from __future__ import annotations"]
        model_names = sorted(
            {
                endpoint.response.model_name
                for endpoint in specification.endpoints
                if endpoint.response.model_name is not None
            }
        )
        schema_names = sorted(
            {
                schema_name
                for endpoint in specification.endpoints
                for schema_name in self._endpoint_schema_names(endpoint)
            }
        )
        if model_names or schema_names:
            imports.append("")
        if model_names:
            imports.append(f"from {module_path}.models import {', '.join(model_names)}")
        if schema_names:
            imports.append(
                f"from {module_path}.schemas import {', '.join(schema_names)}"
            )
        handlers = [
            self._render_handler(endpoint) for endpoint in specification.endpoints
        ]
        return self._join_sections(imports, handlers)

    def _render_handler(self, endpoint: EndpointSpec) -> str:
        response_type = self._response_type(endpoint)
        if endpoint.request is None:
            signature = f"async def {endpoint.handler}() -> {response_type}:"
        else:
            signature = (
                f"async def {endpoint.handler}(\n"
                f"    request: {self._request_type(endpoint)},\n"
                f") -> {response_type}:"
            )
        return (
            f'{signature}\n    raise NotImplementedError("Handler를 구현해야 합니다.")'
        )

    @classmethod
    def _endpoint_schema_names(cls, endpoint: EndpointSpec) -> tuple[str, ...]:
        names: list[str] = []
        if endpoint.request is not None:
            names.append(cls._request_type(endpoint))
        if endpoint.response.model_name is None:
            names.append(cls._response_type(endpoint))
        return tuple(names)

    @classmethod
    def _request_type(cls, endpoint: EndpointSpec) -> str:
        return f"{cls._class_prefix(endpoint)}Request"

    @classmethod
    def _response_type(cls, endpoint: EndpointSpec) -> str:
        if endpoint.response.model_name is not None:
            return endpoint.response.model_name
        return f"{cls._class_prefix(endpoint)}Response"

    def _render_class(self, name: str, fields: list[FieldSpec]) -> str:
        lines = [f"class {name}(BaseModel):"]
        if not fields:
            lines.append("    pass")
            return "\n".join(lines)

        for field in fields:
            annotation = self._type_renderer.render(field.type)
            default = self._render_default(field)
            lines.append(f"    {field.name}: {annotation}{default}")
        return "\n".join(lines)

    @staticmethod
    def _render_default(field: FieldSpec) -> str:
        if field.default is not None:
            return f" = {field.default!r}"
        if field.type.kind is FieldTypeKind.OPTIONAL:
            return " = None"
        return ""

    @staticmethod
    def _class_prefix(endpoint: EndpointSpec) -> str:
        return "".join(part.capitalize() for part in endpoint.name.split("_"))

    @staticmethod
    def _join_sections(imports: list[str], classes: list[str]) -> str:
        return "\n".join(imports) + "\n\n\n" + "\n\n\n".join(classes) + "\n"
