import pytest
from pydantic import ValidationError

from autoforge.core.specification import (
    ApplicationSpec,
    ColumnSpec,
    DatabaseShardSpec,
    DatabaseSpec,
    DatabaseStoreSpec,
    DataPlacementMode,
    DataPlacementSpec,
    EndpointDependency,
    EndpointSpec,
    FieldSpec,
    FieldType,
    FieldTypeKind,
    HttpMethod,
    ModelSpec,
    ModuleInfo,
    ModuleSpec,
    ProjectInfo,
    ProjectSpec,
    RepositoryQuerySpec,
    RepositorySpec,
    ResponseSpec,
    SchemaSpec,
    ServiceSpec,
    TableSpec,
)


def test_create_minimal_project_spec() -> None:
    spec = ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="Game Server",
            package_name="game_server",
            version="0.1.0",
        ),
        application=ApplicationSpec(modules=["tutorial"]),
    )

    assert spec.project.package_name == "game_server"
    assert spec.application.framework == "fastapi"
    assert spec.application.modules == ["tutorial"]


def test_application_service_requires_positive_ttl_and_unique_name() -> None:
    service = ServiceSpec(
        name="session",
        kind="redis_session",
        namespace="kis_session",
        ttl_seconds=3600,
    )
    application = ApplicationSpec(services=[service])

    assert application.services == [service]

    cluster_service = service.model_copy(
        update={"mode": "cluster", "cluster_url_env": "SESSION_CLUSTER_URL"}
    )
    assert cluster_service.mode == "cluster"
    assert cluster_service.cluster_url_env == "SESSION_CLUSTER_URL"

    with pytest.raises(ValidationError, match="greater than 0"):
        ServiceSpec(
            name="session",
            kind="redis_session",
            namespace="kis_session",
            ttl_seconds=0,
        )

    with pytest.raises(ValidationError, match="string_pattern_mismatch"):
        ServiceSpec(
            name="session",
            kind="redis_session",
            namespace="kis_session",
            ttl_seconds=3600,
            url_env="redis-url",
        )

    with pytest.raises(ValidationError, match="Service 이름은 중복"):
        ApplicationSpec(services=[service, service])


def test_endpoint_dependency_is_typed_unique_and_optional() -> None:
    endpoint_data = {
        "name": "login",
        "method": "POST",
        "path": "/login",
        "response": {"fields": []},
        "handler": "login",
    }
    endpoint = EndpointSpec.model_validate(
        {**endpoint_data, "dependencies": ["session_store"]}
    )

    assert endpoint.dependencies == [EndpointDependency.SESSION_STORE]

    database_endpoint = EndpointSpec.model_validate(
        {**endpoint_data, "dependencies": ["database_session_registry"]}
    )
    assert database_endpoint.dependencies == [
        EndpointDependency.DATABASE_SESSION_REGISTRY
    ]

    with pytest.raises(ValidationError, match="dependencies must be unique"):
        EndpointSpec.model_validate(
            {**endpoint_data, "dependencies": ["session_store", "session_store"]}
        )

    with pytest.raises(ValidationError, match="session_store"):
        EndpointSpec.model_validate(
            {**endpoint_data, "dependencies": ["unknown_store"]}
        )


def test_application_database_supports_global_and_sharded_urls() -> None:
    database = DatabaseStoreSpec(
        name="identity",
        global_url_env="IDENTITY_DATABASE_URL",
        shards=[
            DatabaseShardSpec(
                shard_id="1",
                url_env="IDENTITY_SHARD_1_DATABASE_URL",
            )
        ],
    )

    assert ApplicationSpec(databases=[database]).databases == [database]

    with pytest.raises(ValidationError, match="requires a global URL or shard URLs"):
        DatabaseStoreSpec(name="identity")

    with pytest.raises(ValidationError, match="shard IDs must be unique"):
        DatabaseStoreSpec(
            name="identity",
            shards=[
                DatabaseShardSpec(shard_id="1", url_env="SHARD_ONE_URL"),
                DatabaseShardSpec(shard_id="1", url_env="SHARD_TWO_URL"),
            ],
        )


def test_create_tutorial_module_spec() -> None:
    progress_model = ModelSpec(
        name="TutorialProgress",
        fields=[
            FieldSpec(
                name="current_step",
                type=FieldType(kind=FieldTypeKind.INTEGER),
            ),
            FieldSpec(
                name="completed",
                type=FieldType(kind=FieldTypeKind.BOOLEAN),
                default=False,
            ),
        ],
    )
    endpoint = EndpointSpec(
        name="get_progress",
        method=HttpMethod.GET,
        path="/progress",
        response=ResponseSpec(model="TutorialProgress"),
        handler="get_progress",
    )

    spec = ModuleSpec(
        spec_version="1",
        module=ModuleInfo(
            name="tutorial",
            display_name="Tutorial",
            route_prefix="/api/tutorial",
        ),
        models=[progress_model],
        endpoints=[endpoint],
    )

    assert spec.module.name == "tutorial"
    assert spec.endpoints[0].response.model_name == "TutorialProgress"


@pytest.mark.parametrize(
    "name",
    [
        "GameServer",
        "2server",
        "game-server",
        "game server",
        "../server",
        "class",
        "__server",
        "nul",
    ],
)
def test_project_spec_rejects_invalid_package_name(name: str) -> None:
    with pytest.raises(ValidationError):
        ProjectInfo(name="Game Server", package_name=name, version="0.1.0")


def test_project_spec_rejects_unsupported_version_and_framework() -> None:
    with pytest.raises(ValidationError):
        ProjectSpec(
            spec_version="2",
            project=ProjectInfo(
                name="Game Server",
                package_name="game_server",
                version="0.1.0",
            ),
            application={"framework": "django"},
        )


@pytest.mark.parametrize("path", ["progress", "/a//b", "/../secret", r"/a\b"])
def test_endpoint_rejects_invalid_http_path(path: str) -> None:
    with pytest.raises(ValidationError):
        EndpointSpec(
            name="get_progress",
            method=HttpMethod.GET,
            path=path,
            response=ResponseSpec(),
            handler="get_progress",
        )


def test_module_spec_rejects_duplicate_models_and_endpoints() -> None:
    model = ModelSpec(name="TutorialProgress")
    endpoint = EndpointSpec(
        name="get_progress",
        method=HttpMethod.GET,
        path="/progress",
        response=ResponseSpec(model="TutorialProgress"),
        handler="get_progress",
    )

    with pytest.raises(ValidationError, match="Model 이름은 중복"):
        ModuleSpec(
            spec_version="1",
            module=ModuleInfo(
                name="tutorial",
                display_name="Tutorial",
                route_prefix="/api/tutorial",
            ),
            models=[model, model],
        )

    with pytest.raises(ValidationError, match="Endpoint 이름은 중복"):
        ModuleSpec(
            spec_version="1",
            module=ModuleInfo(
                name="tutorial",
                display_name="Tutorial",
                route_prefix="/api/tutorial",
            ),
            models=[model],
            endpoints=[endpoint, endpoint],
        )


def test_module_spec_rejects_unknown_model_reference() -> None:
    endpoint = EndpointSpec(
        name="get_progress",
        method=HttpMethod.GET,
        path="/progress",
        request=SchemaSpec(
            fields=[
                FieldSpec(
                    name="progress",
                    type=FieldType(
                        kind=FieldTypeKind.MODEL,
                        reference="MissingModel",
                    ),
                )
            ]
        ),
        response=ResponseSpec(),
        handler="get_progress",
    )

    with pytest.raises(ValidationError, match="정의되지 않은 Model"):
        ModuleSpec(
            spec_version="1",
            module=ModuleInfo(
                name="tutorial",
                display_name="Tutorial",
                route_prefix="/api/tutorial",
            ),
            endpoints=[endpoint],
        )


def test_create_database_spec_for_global_account_profile() -> None:
    database = DatabaseSpec(
        tables=[
            TableSpec(
                name="user_profiles",
                columns=[
                    ColumnSpec(
                        name="user_id",
                        type=FieldType(kind=FieldTypeKind.UUID),
                        primary_key=True,
                    ),
                    ColumnSpec(
                        name="risk_tolerance",
                        type=FieldType(kind=FieldTypeKind.STRING),
                    ),
                ],
            )
        ],
        repositories=[
            RepositorySpec(
                name="UserProfileRepository",
                aggregate="UserProfile",
                table="user_profiles",
                operations=["find_by_id", "save"],
            )
        ],
        placements=[
            DataPlacementSpec(
                table="user_profiles",
                store="identity",
                mode=DataPlacementMode.GLOBAL,
                partition_key="user_id",
            )
        ],
    )

    spec = ModuleSpec(
        spec_version="1",
        module=ModuleInfo(
            name="account",
            display_name="Account",
            route_prefix="/api/account",
        ),
        models=[ModelSpec(name="UserProfile")],
        database=database,
    )

    assert spec.database is not None
    assert spec.database.provider == "agnostic"
    assert spec.database.repositories[0].operations == ["find_by_id", "save"]
    assert spec.database.placements[0].unresolved_policy == "error"


def test_table_rejects_missing_primary_key_and_duplicate_columns() -> None:
    column = ColumnSpec(
        name="user_id",
        type=FieldType(kind=FieldTypeKind.UUID),
    )

    with pytest.raises(ValidationError, match="Primary Key"):
        TableSpec(name="user_profiles", columns=[column])

    with pytest.raises(ValidationError, match="Column 이름은 중복"):
        TableSpec(
            name="user_profiles",
            columns=[
                column.model_copy(update={"primary_key": True}),
                column.model_copy(update={"primary_key": True}),
            ],
        )


def test_column_rejects_nullable_primary_key_and_nested_types() -> None:
    with pytest.raises(ValidationError, match="nullable"):
        ColumnSpec(
            name="user_id",
            type=FieldType(kind=FieldTypeKind.UUID),
            primary_key=True,
            nullable=True,
        )


def test_column_supports_unique_and_index_constraints() -> None:
    column = ColumnSpec(
        name="email",
        type=FieldType(kind=FieldTypeKind.STRING),
        unique=True,
        index=True,
    )

    assert column.unique is True
    assert column.index is True

    with pytest.raises(ValidationError, match="직접 사용할 수 없습니다"):
        ColumnSpec(
            name="roles",
            type=FieldType(
                kind=FieldTypeKind.LIST,
                item=FieldType(kind=FieldTypeKind.STRING),
            ),
        )


def test_sharded_placement_requires_valid_partition_key() -> None:
    with pytest.raises(ValidationError, match="partition_key가 필요"):
        DataPlacementSpec(
            table="orders",
            store="trading",
            mode=DataPlacementMode.SHARDED,
        )

    with pytest.raises(ValidationError, match="partition_key Column이 없습니다"):
        DatabaseSpec(
            tables=[
                TableSpec(
                    name="orders",
                    columns=[
                        ColumnSpec(
                            name="order_id",
                            type=FieldType(kind=FieldTypeKind.UUID),
                            primary_key=True,
                        )
                    ],
                )
            ],
            placements=[
                DataPlacementSpec(
                    table="orders",
                    store="trading",
                    mode=DataPlacementMode.SHARDED,
                    partition_key="user_id",
                )
            ],
        )


def test_database_rejects_unknown_repository_table_and_aggregate() -> None:
    with pytest.raises(ValidationError, match="참조하는 Table이 없습니다"):
        DatabaseSpec(
            repositories=[
                RepositorySpec(
                    name="UserProfileRepository",
                    aggregate="UserProfile",
                    table="user_profiles",
                    operations=["save"],
                )
            ]
        )

    valid_database = DatabaseSpec(
        tables=[
            TableSpec(
                name="user_profiles",
                columns=[
                    ColumnSpec(
                        name="user_id",
                        type=FieldType(kind=FieldTypeKind.UUID),
                        primary_key=True,
                    )
                ],
            )
        ],
        repositories=[
            RepositorySpec(
                name="UserProfileRepository",
                aggregate="UserProfile",
                table="user_profiles",
                operations=["save"],
            )
        ],
    )

    with pytest.raises(ValidationError, match="Aggregate Model이 없습니다"):
        ModuleSpec(
            spec_version="1",
            module=ModuleInfo(
                name="account",
                display_name="Account",
                route_prefix="/api/account",
            ),
            database=valid_database,
        )


def test_repository_query_requires_unique_existing_column() -> None:
    table = TableSpec(
        name="login_accounts",
        columns=[
            ColumnSpec(
                name="user_id",
                type=FieldType(kind=FieldTypeKind.UUID),
                primary_key=True,
            ),
            ColumnSpec(
                name="email",
                type=FieldType(kind=FieldTypeKind.STRING),
                unique=True,
            ),
            ColumnSpec(
                name="password_hash",
                type=FieldType(kind=FieldTypeKind.STRING),
            ),
        ],
    )

    with pytest.raises(ValidationError, match="참조하는 Column이 없습니다"):
        DatabaseSpec(
            tables=[table],
            repositories=[
                RepositorySpec(
                    name="LoginAccountRepository",
                    aggregate="LoginAccount",
                    table="login_accounts",
                    operations=["save"],
                    queries=[
                        RepositoryQuerySpec(
                            name="find_by_email",
                            column="missing_email",
                        )
                    ],
                )
            ],
        )

    with pytest.raises(ValidationError, match="unique Column"):
        DatabaseSpec(
            tables=[table],
            repositories=[
                RepositorySpec(
                    name="LoginAccountRepository",
                    aggregate="LoginAccount",
                    table="login_accounts",
                    operations=["save"],
                    queries=[
                        RepositoryQuerySpec(
                            name="find_by_password_hash",
                            column="password_hash",
                        )
                    ],
                )
            ],
        )

    with pytest.raises(ValidationError, match="Query 이름은 중복"):
        RepositorySpec(
            name="LoginAccountRepository",
            aggregate="LoginAccount",
            table="login_accounts",
            operations=["save"],
            queries=[
                RepositoryQuerySpec(name="find_by_email", column="email"),
                RepositoryQuerySpec(name="find_by_email", column="email"),
            ],
        )
