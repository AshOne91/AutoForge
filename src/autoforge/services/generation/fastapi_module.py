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
    EndpointAccessLevel,
    EndpointDependency,
    EndpointSpec,
    FieldSpec,
    FieldTypeKind,
    ModuleSpec,
)
from autoforge.core.specification.naming import validate_python_name
from autoforge.services.generation.pydantic_types import PydanticTypeRenderer

MODULE_GENERATOR_ID: Final = "autoforge.generator.fastapi.module"
MODULE_GENERATOR_VERSION: Final = "0.1.1"


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
        has_session_store = self._requires_session_store(specification)
        has_current_session = self._requires_current_session(specification)
        has_database_registry = self._requires_database_registry(specification)
        has_service_token = self._requires_service_token(specification)
        has_access_level = self._requires_access_level(specification)
        has_idempotency = any(endpoint.idempotency for endpoint in specification.endpoints)
        has_dependencies = (
            has_session_store
            or has_current_session
            or has_database_registry
            or has_service_token
            or has_access_level
            or has_idempotency
        )
        fastapi_names = ["APIRouter"]
        if has_dependencies:
            fastapi_names.append("Depends")
        if has_idempotency:
            fastapi_names.extend(["HTTPException", "Request"])
        imports: list[str] = []
        if has_idempotency:
            imports.extend(["import hashlib", "import json"])
        if has_dependencies:
            imports.extend(["from typing import Annotated", ""])
        elif has_idempotency:
            imports.append("")
        imports.append(f"from fastapi import {', '.join(fastapi_names)}")
        if has_idempotency:
            imports.extend([
                "from fastapi.encoders import jsonable_encoder",
                "from fastapi.responses import JSONResponse",
            ])
        imports.append("")
        if has_access_level:
            imports.append(
                self._render_from_import(
                    f"{self._package_name}.infrastructure.access_control",
                    ["AccessLevel", "require_access_level"],
                )
            )
        if has_database_registry:
            imports.extend(
                [
                    self._render_from_import(
                        f"{self._package_name}.infrastructure.database.provider",
                        ["get_session_registry"],
                    ),
                    self._render_from_import(
                        f"{self._package_name}.infrastructure.database.session",
                        ["AsyncSessionRegistry"],
                    ),
                ]
            )
        if has_session_store or has_current_session or has_idempotency:
            protocol_names = []
            provider_names = []
            if has_current_session:
                protocol_names.append("SessionData")
                provider_names.append("get_current_session")
            if has_session_store:
                protocol_names.append("SessionStore")
                provider_names.append("get_session_store")
            if has_idempotency:
                protocol_names.extend(
                    [
                        "ReplayRecord",
                        "RequestReplayConflict",
                        "RequestReplayInProgress",
                        "RequestReplayStore",
                    ]
                )
                provider_names.append("get_request_replay_store")
            protocol_names.sort()
            provider_names.sort()
            imports.extend(
                [
                    self._render_from_import(
                        f"{self._package_name}.infrastructure.session_store.protocol",
                        protocol_names,
                    ),
                    self._render_from_import(
                        f"{self._package_name}.infrastructure.session_store.provider",
                        provider_names,
                    ),
                ]
            )
        if has_service_token:
            imports.append(
                self._render_from_import(
                    f"{self._package_name}.infrastructure.service_tokens",
                    ["require_service_token"],
                )
            )
        if specification.endpoints:
            imports.append(f"from {module_path} import handlers")
        model_names = sorted(
            {
                endpoint.response.model_name
                for endpoint in specification.endpoints
                if endpoint.response.model_name is not None
            }
        )
        if model_names:
            imports.append(
                self._render_from_import(
                    f"{module_path}.generated.models", model_names
                )
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
                self._render_from_import(
                    f"{module_path}.generated.schemas", schema_names
                )
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
        import_section = "\n".join(imports).rstrip()
        endpoint_section = "\n\n\n".join(endpoints)
        rendered = f"{import_section}\n\n{router_declaration}"
        if endpoint_section:
            rendered += f"\n\n\n{endpoint_section}"
        return f"{rendered}\n"

    def _render_router_endpoint(self, endpoint: EndpointSpec) -> str:
        response_type = self._response_type(endpoint)
        method = endpoint.method.value.lower()
        path = json.dumps(endpoint.path, ensure_ascii=False)
        decorator_arguments = [path, f"response_model={response_type}"]
        if endpoint.access_level is not None:
            access_level = EndpointAccessLevel(endpoint.access_level).name
            decorator_arguments.append(
                "dependencies=[Depends(require_access_level("
                f"AccessLevel.{access_level}))]"
            )
        elif endpoint.service_token is not None:
            token_name = json.dumps(endpoint.service_token, ensure_ascii=False)
            decorator_arguments.append(
                f"dependencies=[Depends(require_service_token({token_name}))]"
            )
        lines = [f"@router.{method}({', '.join(decorator_arguments)})"]
        parameters: list[str] = []
        arguments: list[str] = []
        if endpoint.idempotency:
            parameters.append("    http_request: Request,")
        if endpoint.request is not None:
            parameters.append(f"    request: {self._request_type(endpoint)},")
            arguments.append("request")
        if EndpointDependency.SESSION_STORE in endpoint.dependencies:
            parameters.append(
                "    session_store: Annotated["
                "SessionStore, Depends(get_session_store)],"
            )
            arguments.append("session_store")
        if EndpointDependency.CURRENT_SESSION in endpoint.dependencies:
            parameters.append(
                "    current_session: Annotated["
                "SessionData, Depends(get_current_session)],"
            )
            arguments.append("current_session")
        if (
            EndpointDependency.DATABASE_SESSION_REGISTRY
            in endpoint.dependencies
        ):
            parameters.append(
                "    session_registry: Annotated["
                "AsyncSessionRegistry, Depends(get_session_registry)],"
            )
            arguments.append("session_registry")
        if endpoint.idempotency:
            parameters.append(
                "    replay_store: Annotated["
                "RequestReplayStore, Depends(get_request_replay_store)],"
            )

        if parameters:
            lines.append(f"async def {endpoint.name}(")
            lines.extend(parameters)
            lines.append(f") -> {response_type}:")
        else:
            lines.append(f"async def {endpoint.name}() -> {response_type}:")
        joined_arguments = ", ".join(arguments)
        handler_call = f"await handlers.{endpoint.handler}({joined_arguments})"
        if endpoint.idempotency:
            request_body = (
                "request.model_dump_json()" if endpoint.request is not None else '""'
            )
            lines.extend(
                [
                    '    idempotency_key = http_request.headers.get("Idempotency-Key")',
                    "    if not idempotency_key:",
                    '        raise HTTPException(status_code=400, detail="Idempotency-Key header is required")',
                    f'    fingerprint_source = "{endpoint.method.value}:{endpoint.path}:" + {request_body}',
                    '    fingerprint = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()',
                    "    try:",
                    f"        replay = await replay_store.claim(idempotency_key, fingerprint, {endpoint.idempotency_ttl_seconds})",
                    "    except RequestReplayConflict as error:",
                    '        raise HTTPException(status_code=409, detail=str(error)) from error',
                    "    except RequestReplayInProgress as error:",
                    '        raise HTTPException(status_code=409, detail=str(error)) from error',
                    "    if isinstance(replay, ReplayRecord):",
                    "        return JSONResponse(status_code=replay.status_code, content=json.loads(replay.body))",
                    "    try:",
                    f"        result = {handler_call}",
                    '        body = json.dumps(jsonable_encoder(result), separators=(",", ":"))',
                    "        await replay_store.complete(replay, 200, body)",
                    "        return result",
                    "    except Exception:",
                    "        await replay_store.abort(replay)",
                    "        raise",
                ]
            )
        else:
            lines.append(f"    return {handler_call}")
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
        if self._requires_database_registry(specification):
            imports.append(
                f"from {self._package_name}.infrastructure.database.session "
                "import AsyncSessionRegistry"
            )
        protocol_names = []
        if self._requires_current_session(specification):
            protocol_names.append("SessionData")
        if self._requires_session_store(specification):
            protocol_names.append("SessionStore")
        if protocol_names:
            imports.append(
                self._render_from_import(
                    f"{self._package_name}.infrastructure.session_store.protocol",
                    protocol_names,
                )
            )
        if model_names:
            imports.append(
                self._render_from_import(f"{module_path}.models", model_names)
            )
        if schema_names:
            imports.append(
                self._render_from_import(f"{module_path}.schemas", schema_names)
            )
        handlers = [
            self._render_handler(endpoint) for endpoint in specification.endpoints
        ]
        return self._join_sections(imports, handlers)

    def _render_handler(self, endpoint: EndpointSpec) -> str:
        response_type = self._response_type(endpoint)
        parameters: list[str] = []
        if endpoint.request is not None:
            parameters.append(f"    request: {self._request_type(endpoint)},")
        if EndpointDependency.SESSION_STORE in endpoint.dependencies:
            parameters.append("    session_store: SessionStore,")
        if EndpointDependency.CURRENT_SESSION in endpoint.dependencies:
            parameters.append("    current_session: SessionData,")
        if (
            EndpointDependency.DATABASE_SESSION_REGISTRY
            in endpoint.dependencies
        ):
            parameters.append("    session_registry: AsyncSessionRegistry,")
        if parameters:
            signature = (
                f"async def {endpoint.handler}(\n"
                + "\n".join(parameters)
                + f"\n) -> {response_type}:"
            )
        else:
            signature = f"async def {endpoint.handler}() -> {response_type}:"
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

    @staticmethod
    def _render_from_import(module: str, names: list[str]) -> str:
        single_line = f"from {module} import {', '.join(names)}"
        if len(single_line) <= 88:
            return single_line
        items = "".join(f"    {name},\n" for name in names)
        return f"from {module} import (\n{items})"

    @staticmethod
    def _requires_session_store(specification: ModuleSpec) -> bool:
        return any(
            EndpointDependency.SESSION_STORE in endpoint.dependencies
            for endpoint in specification.endpoints
        )

    @staticmethod
    def _requires_current_session(specification: ModuleSpec) -> bool:
        return any(
            EndpointDependency.CURRENT_SESSION in endpoint.dependencies
            for endpoint in specification.endpoints
        )

    @staticmethod
    def _requires_database_registry(specification: ModuleSpec) -> bool:
        return any(
            EndpointDependency.DATABASE_SESSION_REGISTRY
            in endpoint.dependencies
            for endpoint in specification.endpoints
        )

    @staticmethod
    def _requires_service_token(specification: ModuleSpec) -> bool:
        return any(
            endpoint.service_token is not None
            for endpoint in specification.endpoints
        )

    @staticmethod
    def _requires_access_level(specification: ModuleSpec) -> bool:
        return any(
            endpoint.access_level is not None
            for endpoint in specification.endpoints
        )
