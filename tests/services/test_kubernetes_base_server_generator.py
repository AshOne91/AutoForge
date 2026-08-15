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
    KubernetesSpec,
    ProjectInfo,
    ProjectSpec,
    ServiceSpec,
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
                ServiceSpec(
                    name="events",
                    kind="rabbitmq",
                    outbox_stores=["identity"],
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
            }
        },
    )


def test_kubernetes_base_server_generator_satisfies_protocol() -> None:
    generator: Generator[ProjectSpec] = KubernetesBaseServerGenerator()

    assert isinstance(generator, Generator)


def test_render_is_empty_until_kubernetes_is_enabled() -> None:
    assert KubernetesBaseServerGenerator().render(base_server_specification()) == {}


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
    assert "hostPath is node-local" in readme


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
