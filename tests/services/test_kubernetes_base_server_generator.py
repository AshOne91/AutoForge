from pathlib import PurePosixPath

import pytest
import yaml
from pydantic import ValidationError

from autoforge.core.generation import FileOwnership, Generator, content_hash
from autoforge.core.specification import (
    ApplicationSpec,
    DatabaseShardSpec,
    DatabaseStoreSpec,
    DurableJobSpec,
    ElkSpec,
    KubernetesControlPlaneSpec,
    KubernetesSpec,
    ProjectInfo,
    ProjectSpec,
    RuntimeEnvironmentSpec,
    ServiceSpec,
    ServiceTokenSpec,
    ToolingSpec,
)
from autoforge.services.generation.kubernetes import KubernetesBaseServerGenerator


def base_server_specification(
    *,
    enabled: bool = False,
    collector_enabled: bool = False,
    durable_jobs: bool = False,
    application_replicas: int = 3,
    proxy_replicas: int = 2,
    mysql_ha: bool = False,
    mysql_operator: bool = False,
    control_plane: bool = False,
) -> ProjectSpec:
    return ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="KIS Auto Trading",
            package_name="kis_auto_trading",
            version="0.1.0",
        ),
        application=ApplicationSpec(
            databases=[
                DatabaseStoreSpec(
                    name="identity", global_url_env="IDENTITY_DATABASE_URL"
                ),
                DatabaseStoreSpec(
                    name="account",
                    shards=[
                        DatabaseShardSpec(
                            shard_id="1", url_env="ACCOUNT_SHARD_1_DATABASE_URL"
                        )
                    ],
                ),
            ],
            services=[
                ServiceSpec(
                    name="session",
                    kind="redis_session",
                    namespace="kis_session",
                    ttl_seconds=3600,
                    mode="cluster",
                ),
                *(
                    []
                    if mysql_ha
                    else [
                        ServiceSpec(
                            name="events",
                            kind="rabbitmq",
                            outbox_stores=["identity"],
                        )
                    ]
                ),
            ],
            durable_jobs=[
                DurableJobSpec(
                    name="news_collection",
                    store="identity",
                    event_type="news.collection.requested",
                    routing_key="news.collection.requested",
                )
            ]
            if durable_jobs
            else [],
        ),
        tooling={
            "elk": {
                "enabled": collector_enabled,
                "kubernetes_collector_enabled": collector_enabled,
            },
            "kubernetes": {
                "enabled": enabled,
                "image": "kis-auto-trading:latest",
                "secret_name": "kis-runtime",
                "application_replicas": application_replicas,
                "proxy_replicas": proxy_replicas,
                "log_host_path": "/run/desktop/mnt/host/c/kis-auto-trading/logs",
                "additional_secret_env_names": ["KIS_APP_KEY"],
                **(
                    {
                        "mysql_operator": {
                            "enabled": True,
                            "bootstrap_secret_name": "mysql-operator-bootstrap",
                            "tls_secret_name": "mysql-operator-tls",
                            "cluster_name": "identity-mysql",
                            "mysql_version": "8.4.8",
                            "instances": 3,
                            "router_instances": 2,
                            "storage_class_name": "fast-ssd",
                            "storage_size": "40Gi",
                        }
                    }
                    if mysql_operator
                    else {}
                ),
                **(
                    {
                        "control_plane": {
                            "enabled": True,
                            "image": "autoforge-control-plane:latest",
                            "secret_name": "autoforge-control-plane",
                            "replicas": 2,
                        }
                    }
                    if control_plane
                    else {}
                ),
            },
            **(
                {
                    "local_environment": {
                        "enabled": True,
                        "database_provider": "mysql",
                        "mysql_mode": "ha",
                    }
                }
                if mysql_ha
                else {}
            ),
        },
    )


def test_kubernetes_base_server_generator_satisfies_protocol() -> None:
    generator: Generator[ProjectSpec] = KubernetesBaseServerGenerator()

    assert isinstance(generator, Generator)


def test_render_is_empty_until_kubernetes_is_enabled() -> None:
    assert KubernetesBaseServerGenerator().render(base_server_specification()) == {}


def test_runtime_environments_flow_to_kubernetes_secret_references() -> None:
    specification = base_server_specification(enabled=True)
    application = specification.application.model_copy(
        update={
            "runtime_environments": [
                RuntimeEnvironmentSpec(name="PAYMENTS_API_KEY"),
                RuntimeEnvironmentSpec(name="PAYMENTS_API_SECRET"),
            ]
        }
    )

    files = KubernetesBaseServerGenerator().render(
        specification.model_copy(update={"application": application})
    )
    manifest = files[PurePosixPath("deploy", "kubernetes", "base-server.yaml")]
    secret_environment = files[
        PurePosixPath("deploy", "kubernetes", "secret.env.example")
    ]

    assert "key: PAYMENTS_API_KEY" in manifest
    assert "key: PAYMENTS_API_SECRET" in manifest
    assert "PAYMENTS_API_KEY=\n" in secret_environment
    assert "PAYMENTS_API_SECRET=\n" in secret_environment


def test_render_creates_zero_secret_proxy_and_application_topology() -> None:
    files = KubernetesBaseServerGenerator().render(
        base_server_specification(enabled=True)
    )

    manifest = files[PurePosixPath("deploy", "kubernetes", "base-server.yaml")]
    readme = files[PurePosixPath("deploy", "kubernetes", "README.md")]
    secret_environment = files[
        PurePosixPath("deploy", "kubernetes", "secret.env.example")
    ]

    assert "kind: ConfigMap" in manifest
    assert "default.conf.template" in manifest
    assert "proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;" in manifest
    assert "proxy_set_header X-Forwarded-Proto $scheme;" in manifest
    assert "replicas: 3" in manifest
    assert "replicas: 2" in manifest
    assert "name: kis-auto-trading-backend" in manifest
    assert "type: ClusterIP" in manifest
    assert "name: kis-auto-trading-load-balancer" in manifest
    assert "type: LoadBalancer" in manifest
    assert "port: 8080" in manifest
    assert "secretKeyRef:" in manifest
    assert "key: IDENTITY_DATABASE_URL" in manifest
    assert "key: ACCOUNT_SHARD_1_DATABASE_URL" in manifest
    assert "key: REDIS_CLUSTER_URL" in manifest
    assert "redis-server" not in manifest
    assert "image: redis:" not in manifest
    assert "key: RABBITMQ_URL" in manifest
    assert "key: KIS_APP_KEY" in manifest
    assert "mountPath: /app/logs" in manifest
    assert "name: LOG_DIRECTORY" in manifest
    assert "value: /app/logs" in manifest
    assert "change-me" not in manifest
    assert "IDENTITY_DATABASE_URL=\n" in secret_environment
    assert "KIS_APP_KEY=\n" in secret_environment
    assert "=" in secret_environment
    assert "postgresql://" not in secret_environment
    assert "kubectl create secret generic kis-runtime" in readme
    assert "Copy-Item secret.env.example kis_secret.env" in readme
    assert "kubectl apply" in readme
    assert "Secret values" in readme
    assert "Database topology is provider-owned." in readme
    assert "does not create database clusters, Routers, or StatefulSets." in readme
    assert "hostPath is node-local" in readme
    assert PurePosixPath("deploy", "kubernetes", "mysql-operator.yaml") not in files
    documents = list(yaml.safe_load_all(manifest))
    application = next(
        document
        for document in documents
        if document["kind"] == "Deployment"
        and document["metadata"]["name"] == "kis-auto-trading"
    )
    container = application["spec"]["template"]["spec"]["containers"][0]
    assert container["readinessProbe"]["httpGet"]["path"] == "/readiness"
    assert container["livenessProbe"]["httpGet"]["path"] == "/health"


def test_render_creates_opt_in_control_plane_profile_separately() -> None:
    files = KubernetesBaseServerGenerator().render(
        base_server_specification(enabled=True, control_plane=True)
    )

    manifest = files[PurePosixPath("deploy", "kubernetes", "control-plane.yaml")]
    documents = list(yaml.safe_load_all(manifest))
    secret_environment = files[
        PurePosixPath(
            "deploy", "kubernetes", "control-plane-secret.env.example"
        )
    ]
    base_manifest = files[PurePosixPath("deploy", "kubernetes", "base-server.yaml")]
    readme = files[PurePosixPath("deploy", "kubernetes", "README.md")]

    assert [document["kind"] for document in documents] == ["Deployment", "Service"]
    deployment, service = documents
    assert deployment["metadata"]["name"] == "kis-auto-trading-control-plane"
    assert deployment["spec"]["replicas"] == 2
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    assert container["image"] == "autoforge-control-plane:latest"
    assert container["env"][0]["valueFrom"]["secretKeyRef"]["key"] == (
        "AUTOFORGE_DATABASE_URL"
    )
    assert container["readinessProbe"]["httpGet"]["path"] == "/readiness"
    assert container["livenessProbe"]["httpGet"]["path"] == "/health"
    assert service["spec"]["type"] == "ClusterIP"
    assert service["metadata"]["name"] == "kis-auto-trading-control-plane"
    assert "AUTOFORGE_DATABASE_URL=\n" in secret_environment
    assert "AUTOFORGE_CONTROL_PLANE_TOKEN=\n" in secret_environment
    assert "control-plane" not in base_manifest
    assert "control-plane.yaml" in readme
    assert "does not create a database, migration Job" in readme


def test_render_creates_opt_in_mysql_operator_cluster_manifest() -> None:
    files = KubernetesBaseServerGenerator().render(
        base_server_specification(enabled=True, mysql_operator=True)
    )

    manifest = files[PurePosixPath("deploy", "kubernetes", "mysql-operator.yaml")]
    document = yaml.safe_load(manifest)
    readme = files[PurePosixPath("deploy", "kubernetes", "README.md")]
    bootstrap_environment = files[
        PurePosixPath(
            "deploy", "kubernetes", "mysql-operator-bootstrap.env.example"
        )
    ]

    assert document["apiVersion"] == "mysql.oracle.com/v2"
    assert document["kind"] == "InnoDBCluster"
    assert document["metadata"]["name"] == "identity-mysql"
    assert document["spec"]["secretName"] == "mysql-operator-bootstrap"
    assert document["spec"]["tlsSecretName"] == "mysql-operator-tls"
    assert document["spec"]["tlsCASecretName"] == "identity-mysql-ca"
    assert document["spec"]["instances"] == 3
    assert document["spec"]["router"]["instances"] == 2
    assert document["spec"]["datadirVolumeClaimTemplate"]["storageClassName"] == "fast-ssd"
    assert document["spec"]["datadirVolumeClaimTemplate"]["resources"]["requests"]["storage"] == "40Gi"
    assert "mysql-operator.yaml" in readme
    assert "does not install the Operator" in readme
    assert "a MySQL Operator InnoDBCluster declaration" in readme
    assert "rootUser=\nrootHost=\nrootPassword=\n" == bootstrap_environment
    assert "Copy-Item mysql-operator-bootstrap.env.example mysql_operator_bootstrap.env" in readme
    assert "kubectl create secret generic mysql-operator-bootstrap" in readme
    assert "mysql-operator-tls" in readme
    assert "identity-mysql-ca" in readme


def test_render_keeps_mysql_ha_as_an_external_kubernetes_database_provider() -> None:
    files = KubernetesBaseServerGenerator().render(
        base_server_specification(enabled=True, mysql_ha=True)
    )

    manifest = files[PurePosixPath("deploy", "kubernetes", "base-server.yaml")]

    assert "secretKeyRef:" in manifest
    assert "key: IDENTITY_DATABASE_URL" in manifest
    assert "key: ACCOUNT_SHARD_1_DATABASE_URL" in manifest
    assert "kind: StatefulSet" not in manifest
    assert "mysql-ha-" not in manifest
    assert "mysql-router" not in manifest
    assert "mysql:6446" not in manifest


def test_render_uses_independent_replica_values() -> None:
    files = KubernetesBaseServerGenerator().render(
        base_server_specification(
            enabled=True,
            application_replicas=5,
            proxy_replicas=4,
        )
    )

    manifest = files[PurePosixPath("deploy", "kubernetes", "base-server.yaml")]
    deployments = {
        document["metadata"]["labels"]["app.kubernetes.io/component"]: document
        for document in yaml.safe_load_all(manifest)
        if document.get("kind") == "Deployment"
    }

    assert deployments["application"]["spec"]["replicas"] == 5
    assert deployments["proxy"]["spec"]["replicas"] == 4


def test_render_adds_durable_job_api_token_only_for_durable_jobs() -> None:
    files = KubernetesBaseServerGenerator().render(
        base_server_specification(enabled=True, durable_jobs=True)
    )

    manifest = files[PurePosixPath("deploy", "kubernetes", "base-server.yaml")]
    secret_environment = files[
        PurePosixPath("deploy", "kubernetes", "secret.env.example")
    ]

    assert "key: DURABLE_JOB_API_TOKEN" in manifest
    assert "DURABLE_JOB_API_TOKEN=\n" in secret_environment


def test_render_adds_declared_service_token_to_application_secret() -> None:
    specification = base_server_specification(enabled=True)
    application = specification.application.model_copy(
        update={
            "service_tokens": [
                ServiceTokenSpec(
                    name="operator", token_env="OPERATOR_API_TOKEN"
                )
            ]
        }
    )

    files = KubernetesBaseServerGenerator().render(
        specification.model_copy(update={"application": application})
    )
    manifest = files[PurePosixPath("deploy", "kubernetes", "base-server.yaml")]
    secret_environment = files[
        PurePosixPath("deploy", "kubernetes", "secret.env.example")
    ]

    assert "key: OPERATOR_API_TOKEN" in manifest
    assert "OPERATOR_API_TOKEN=\n" in secret_environment


def test_plan_marks_base_server_manifest_generated() -> None:
    generator = KubernetesBaseServerGenerator()
    specification = base_server_specification(enabled=True)
    rendered = generator.render(specification)

    plan = generator.plan(specification)

    assert len(plan.files) == len(rendered)
    for planned_file in plan.files:
        assert planned_file.ownership is FileOwnership.GENERATED
        assert planned_file.expected_content_hash == content_hash(
            rendered[planned_file.relative_path]
        )


def test_render_creates_filebeat_daemonset_only_when_requested() -> None:
    files = KubernetesBaseServerGenerator().render(
        base_server_specification(enabled=True, collector_enabled=True)
    )

    collector = files[
        PurePosixPath("deploy", "kubernetes", "observability-filebeat.yaml")
    ]
    secret_environment = files[
        PurePosixPath("deploy", "kubernetes", "secret.env.example")
    ]
    base_manifest = files[PurePosixPath("deploy", "kubernetes", "base-server.yaml")]

    assert "kind: DaemonSet" in collector
    assert "kind: ConfigMap" in collector
    assert "docker.elastic.co/beats/filebeat:8.19.17" in collector
    assert "key: ELASTICSEARCH_API_KEY" in collector
    assert "path: /run/desktop/mnt/host/c/kis-auto-trading/logs/.filebeat-data" in collector
    assert "privileged: true" not in collector
    assert "ELASTICSEARCH_HOST=\n" in secret_environment
    assert "ELASTICSEARCH_API_KEY=\n" in secret_environment
    assert "ELASTICSEARCH_API_KEY" not in base_manifest
    assert [document["kind"] for document in yaml.safe_load_all(collector)] == [
        "ConfigMap",
        "DaemonSet",
    ]


def test_enabled_profile_requires_image_and_secret_name() -> None:
    with pytest.raises(ValidationError, match="requires an image"):
        KubernetesSpec(enabled=True)

    with pytest.raises(ValidationError, match="requires a secret_name"):
        KubernetesSpec(enabled=True, image="example:latest")

    with pytest.raises(ValidationError, match="requires an image"):
        KubernetesControlPlaneSpec(enabled=True, secret_name="control-plane")

    with pytest.raises(ValidationError, match="requires a secret_name"):
        KubernetesControlPlaneSpec(enabled=True, image="example:latest")

    with pytest.raises(ValidationError, match="requires Kubernetes base_server"):
        KubernetesSpec(
            control_plane=KubernetesControlPlaneSpec(
                enabled=True,
                image="example:latest",
                secret_name="control-plane",
            )
        )


def test_kubernetes_collector_requires_elk_and_log_host_path() -> None:
    profile = KubernetesSpec(
        enabled=True,
        image="example:latest",
        secret_name="runtime",
    )

    with pytest.raises(ValidationError, match="requires tooling.elk.enabled"):
        ToolingSpec(
            kubernetes=profile,
            elk=ElkSpec(kubernetes_collector_enabled=True),
        )

    with pytest.raises(ValidationError, match="requires log_host_path"):
        ToolingSpec(
            kubernetes=profile,
            elk=ElkSpec(enabled=True, kubernetes_collector_enabled=True),
        )
