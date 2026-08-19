import pytest
from pydantic import ValidationError

from autoforge.core.specification import (
    ApplicationSpec,
    CiProvider,
    CiSpec,
    CiWorkflow,
    ColumnSpec,
    ControlPlaneHeartbeatSpec,
    DatabaseShardSpec,
    DatabaseSpec,
    DatabaseStoreSpec,
    DataPlacementMode,
    DataPlacementSpec,
    DurableJobSpec,
    ElkSpec,
    EndpointAccessLevel,
    EndpointDependency,
    EndpointSpec,
    FieldSpec,
    FieldType,
    FieldTypeKind,
    HttpMethod,
    KubernetesMySQLOperatorSpec,
    KubernetesSpec,
    LocalEnvironmentSpec,
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
    ServiceTokenSpec,
    TableSpec,
    ToolingSpec,
)


def test_durable_job_requires_declared_rabbitmq_outbox_store() -> None:
    job = DurableJobSpec(
        name="news_collection",
        store="account",
        event_type="news.collection.requested",
        routing_key="news.collection.requested",
    )
    service = ServiceSpec(
        name="events",
        kind="rabbitmq",
        outbox_stores=["account"],
    )
    database = DatabaseStoreSpec(
        name="account",
        global_url_env="ACCOUNT_DATABASE_URL",
    )

    application = ApplicationSpec(
        services=[service], databases=[database], durable_jobs=[job]
    )

    assert application.durable_jobs == [job]
    with pytest.raises(ValidationError, match="Durable job stores"):
        ApplicationSpec(
            services=[
                ServiceSpec(
                    name="events",
                    kind="rabbitmq",
                    outbox_stores=["other"],
                )
            ],
            databases=[
                DatabaseStoreSpec(
                    name="other", global_url_env="OTHER_DATABASE_URL"
                )
            ],
            durable_jobs=[job],
        )
    with pytest.raises(ValidationError, match="require a RabbitMQ outbox"):
        ApplicationSpec(databases=[database], durable_jobs=[job])
    with pytest.raises(ValidationError, match="require a global database URL"):
        ApplicationSpec(
            services=[service],
            databases=[
                DatabaseStoreSpec(
                    name="account",
                    shards=[
                        DatabaseShardSpec(
                            shard_id="1", url_env="ACCOUNT_SHARD_1_URL"
                        )
                    ],
                )
            ],
            durable_jobs=[job],
        )
    with pytest.raises(ValidationError, match="schedule must not be empty"):
        DurableJobSpec(
            name="news_collection",
            store="account",
            event_type="news.collection.requested",
            routing_key="news.collection.requested",
            schedule=" ",
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
    assert spec.tooling.ruff_exclude == []
    assert spec.tooling.ci.providers == []
    assert spec.tooling.docker.enabled is False


def test_control_plane_heartbeat_is_opt_in_and_rejects_duplicate_environment_names() -> None:
    assert ApplicationSpec().control_plane_heartbeat.enabled is False
    with pytest.raises(ValidationError, match="endpoint_env and token_env must differ"):
        ControlPlaneHeartbeatSpec(
            enabled=True,
            endpoint_env="CONTROL_PLANE_HEARTBEAT_URL",
            token_env="CONTROL_PLANE_HEARTBEAT_URL",
        )

    with pytest.raises(ValidationError, match="package_name of at most 128"):
        ProjectSpec(
            spec_version="1",
            project=ProjectInfo(
                name="Example",
                package_name=f"service_{'x' * 121}",
                version="0.1.0",
            ),
            application=ApplicationSpec(
                control_plane_heartbeat=ControlPlaneHeartbeatSpec(enabled=True)
            ),
        )


@pytest.mark.parametrize(
    "path",
    ["../outside", "/absolute", "C:/windows", "nested\\windows"],
)
def test_tooling_rejects_unsafe_ruff_exclude_paths(path: str) -> None:
    with pytest.raises(ValidationError):
        ToolingSpec(ruff_exclude=[path])


def test_tooling_normalizes_and_rejects_duplicate_ruff_exclude_paths() -> None:
    tooling = ToolingSpec(ruff_exclude=["reference/base_server", "test.py"])

    assert tooling.ruff_exclude == ["reference/base_server", "test.py"]
    with pytest.raises(ValidationError, match="must be unique"):
        ToolingSpec(ruff_exclude=["reference", "reference"])


def test_project_rejects_published_host_port_collisions() -> None:
    application = ApplicationSpec(
        databases=[DatabaseStoreSpec(name="identity", global_url_env="IDENTITY_URL")]
    )
    tooling = ToolingSpec(
        local_environment=LocalEnvironmentSpec(
            enabled=True, application_enabled=True, host_port_base=49400
        ),
        elk=ElkSpec(enabled=True, host_port_base=49400),
    )

    with pytest.raises(ValidationError, match="49400.*local application.*central ELK"):
        ProjectSpec(
            spec_version="1",
            project=ProjectInfo(name="Example", package_name="example", version="0.1.0"),
            application=application,
            tooling=tooling,
        )


def test_local_environment_database_provider_defaults_to_postgresql() -> None:
    environment = LocalEnvironmentSpec()

    assert environment.database_provider == "postgresql"
    assert environment.rabbitmq_mode == "standalone"
    assert environment.airflow_scheduler_replicas == 1
    assert LocalEnvironmentSpec(database_provider="mysql").postgres_mode == "standalone"
    with pytest.raises(ValidationError, match="postgres_mode=standalone"):
        LocalEnvironmentSpec(database_provider="mysql", postgres_mode="ha")


def test_kubernetes_mysql_operator_profile_requires_ha_inputs_and_secret_split() -> None:
    with pytest.raises(ValidationError, match="bootstrap_secret_name"):
        KubernetesMySQLOperatorSpec(enabled=True)

    profile = KubernetesMySQLOperatorSpec(
        enabled=True,
        bootstrap_secret_name="mysql-operator-bootstrap",
        tls_secret_name="mysql-operator-tls",
        cluster_name="identity-mysql",
        mysql_version="8.4.8",
        instances=3,
        router_instances=2,
        storage_class_name="fast-ssd",
        storage_size="40Gi",
    )

    with pytest.raises(ValidationError, match="requires Kubernetes base_server"):
        KubernetesSpec(mysql_operator=profile)
    with pytest.raises(ValidationError, match="separate bootstrap Secret"):
        KubernetesSpec(
            enabled=True,
            image="example:latest",
            secret_name="mysql-operator-bootstrap",
            mysql_operator=profile,
        )

    specification = KubernetesSpec(
        enabled=True,
        image="example:latest",
        secret_name="application-runtime",
        mysql_operator=profile,
    )

    assert specification.mysql_operator.cluster_name == "identity-mysql"


def test_local_rabbitmq_cluster_requires_one_quorum_service() -> None:
    database = DatabaseStoreSpec(name="automation", global_url_env="AUTOMATION_URL")
    classic_service = ServiceSpec(
        name="events", kind="rabbitmq", outbox_stores=["automation"]
    )
    tooling = ToolingSpec(
        local_environment=LocalEnvironmentSpec(enabled=True, rabbitmq_mode="cluster")
    )
    project = ProjectInfo(name="Example", package_name="example", version="0.1.0")

    with pytest.raises(ValidationError, match="requires queue_type=quorum"):
        ProjectSpec(
            spec_version="1",
            project=project,
            application=ApplicationSpec(
                databases=[database], services=[classic_service]
            ),
            tooling=tooling,
        )

    specification = ProjectSpec(
        spec_version="1",
        project=project,
        application=ApplicationSpec(
            databases=[database],
            services=[classic_service.model_copy(update={"queue_type": "quorum"})],
        ),
        tooling=tooling,
    )

    assert specification.tooling.local_environment.rabbitmq_mode == "cluster"


def test_local_airflow_scheduler_ha_requires_durable_jobs_and_postgres_ha() -> None:
    database = DatabaseStoreSpec(name="automation", global_url_env="AUTOMATION_URL")
    service = ServiceSpec(name="events", kind="rabbitmq", outbox_stores=["automation"])
    job = DurableJobSpec(
        name="news_collection",
        store="automation",
        event_type="news.collection.requested",
        routing_key="news.collection.requested",
    )
    project = ProjectInfo(name="Example", package_name="example", version="0.1.0")

    with pytest.raises(ValidationError, match="requires durable jobs"):
        ProjectSpec(
            spec_version="1",
            project=project,
            application=ApplicationSpec(databases=[database], services=[service]),
            tooling=ToolingSpec(
                local_environment=LocalEnvironmentSpec(
                    enabled=True,
                    postgres_mode="ha",
                    airflow_scheduler_replicas=2,
                )
            ),
        )
    with pytest.raises(ValidationError, match="requires postgres_mode=ha"):
        ProjectSpec(
            spec_version="1",
            project=project,
            application=ApplicationSpec(
                databases=[database], services=[service], durable_jobs=[job]
            ),
            tooling=ToolingSpec(
                local_environment=LocalEnvironmentSpec(
                    enabled=True, airflow_scheduler_replicas=2
                )
            ),
        )

    specification = ProjectSpec(
        spec_version="1",
        project=project,
        application=ApplicationSpec(
            databases=[database], services=[service], durable_jobs=[job]
        ),
        tooling=ToolingSpec(
            local_environment=LocalEnvironmentSpec(
                enabled=True,
                postgres_mode="ha",
                airflow_scheduler_replicas=2,
            )
        ),
    )

    assert specification.tooling.local_environment.airflow_scheduler_replicas == 2


def test_ci_spec_requires_a_test_workflow_and_unique_providers() -> None:
    ci = CiSpec(
        providers=[CiProvider.GITHUB_ACTIONS, CiProvider.JENKINS],
        workflows=[CiWorkflow.TEST, CiWorkflow.BUILD],
    )

    assert ci.providers == [CiProvider.GITHUB_ACTIONS, CiProvider.JENKINS]
    with pytest.raises(ValidationError, match="must include test"):
        CiSpec(workflows=[CiWorkflow.BUILD])
    with pytest.raises(ValidationError, match="must be unique"):
        CiSpec(providers=[CiProvider.GITHUB_ACTIONS, CiProvider.GITHUB_ACTIONS])


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
    assert cluster_service.cluster_startup_nodes_env == "REDIS_CLUSTER_STARTUP_NODES"

    with pytest.raises(ValidationError, match="ttl_seconds must be positive"):
        ServiceSpec(
            name="session",
            kind="redis_session",
            namespace="kis_session",
            ttl_seconds=0,
        )


def test_rabbitmq_service_requires_declared_outbox_store() -> None:
    service = ServiceSpec(
        name="events",
        kind="rabbitmq",
        outbox_stores=["account"],
    )

    application = ApplicationSpec(
        services=[service],
        databases=[
            DatabaseStoreSpec(
                name="account",
                shards=[DatabaseShardSpec(shard_id="1", url_env="ACCOUNT_URL")],
            )
        ],
    )

    assert application.services == [service]
    with pytest.raises(ValidationError, match="outbox store"):
        ApplicationSpec(services=[service])

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


def test_service_tokens_require_unique_names_and_secret_environments() -> None:
    token = ServiceTokenSpec(name="operator", token_env="OPERATOR_API_TOKEN")

    application = ApplicationSpec(service_tokens=[token])

    assert application.service_token_environments == {
        "operator": "OPERATOR_API_TOKEN"
    }
    with pytest.raises(ValidationError, match="token names must be unique"):
        ApplicationSpec(service_tokens=[token, token])
    with pytest.raises(ValidationError, match="token environments must be unique"):
        ApplicationSpec(
            service_tokens=[
                token,
                ServiceTokenSpec(name="reporting", token_env="OPERATOR_API_TOKEN"),
            ]
        )


def test_endpoint_service_token_is_optional_and_typed() -> None:
    endpoint = EndpointSpec.model_validate(
        {
            "name": "search",
            "method": "GET",
            "path": "/search",
            "response": {"fields": []},
            "handler": "search",
            "service_token": "operator",
        }
    )

    assert endpoint.service_token == "operator"
    with pytest.raises(ValidationError, match="소문자로 시작"):
        EndpointSpec.model_validate(
            {
                "name": "search",
                "method": "GET",
                "path": "/search",
                "response": {"fields": []},
                "handler": "search",
                "service_token": "operator-token",
            }
        )


def test_endpoint_access_level_requires_a_human_session_and_excludes_service_token() -> None:
    endpoint_data = {
        "name": "manage_accounts",
        "method": "GET",
        "path": "/accounts",
        "response": {"fields": []},
        "handler": "manage_accounts",
        "dependencies": ["current_session"],
        "access_level": "operator",
    }

    endpoint = EndpointSpec.model_validate(endpoint_data)

    assert endpoint.access_level is EndpointAccessLevel.OPERATOR
    with pytest.raises(ValidationError, match="current_session"):
        EndpointSpec.model_validate(
            {**endpoint_data, "dependencies": []}
        )
    with pytest.raises(ValidationError, match="cannot be combined"):
        EndpointSpec.model_validate(
            {**endpoint_data, "service_token": "operator"}
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


@pytest.mark.parametrize("dependencies", [[""], ["yfinance", "yfinance"]])
def test_project_spec_rejects_empty_or_duplicate_dependencies(
    dependencies: list[str],
) -> None:
    with pytest.raises(ValidationError):
        ProjectInfo(
            name="Game Server",
            package_name="game_server",
            version="0.1.0",
            dependencies=dependencies,
        )


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
