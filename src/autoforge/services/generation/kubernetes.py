from pathlib import PurePosixPath

from autoforge.core.generation import (
    FileOwnership,
    GenerationPlan,
    PlannedAction,
    PlannedFile,
    content_hash,
    specification_hash,
)
from autoforge.core.specification import (
    ProjectSpec,
    RuntimeEnvironmentTarget,
    ServiceSpec,
)

KUBERNETES_BASE_SERVER_GENERATOR_ID = "autoforge.generator.kubernetes-base-server"
KUBERNETES_BASE_SERVER_GENERATOR_VERSION = "0.3.0"
_COLLECTOR_SECRET_ENVIRONMENT_NAMES = (
    "ELASTICSEARCH_HOST",
    "ELASTICSEARCH_API_KEY",
)


class KubernetesBaseServerGenerator:
    """Generate the zero-secret Kubernetes Proxy/App base_server topology."""

    @property
    def generator_id(self) -> str:
        return KUBERNETES_BASE_SERVER_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return KUBERNETES_BASE_SERVER_GENERATOR_VERSION

    def render(self, specification: ProjectSpec) -> dict[PurePosixPath, str]:
        profile = specification.tooling.kubernetes
        if not profile.enabled:
            return {}
        application_name = self._kubernetes_name(specification.project.package_name)
        secret_environment_names = self._secret_environment_names(
            specification, target=RuntimeEnvironmentTarget.APPLICATION
        )
        durable_job_worker_secret_environment_names = (
            self._durable_job_worker_secret_environment_names(specification)
            if specification.application.durable_jobs
            else []
        )
        all_secret_environment_names = self._secret_environment_names(specification)
        collector_enabled = specification.tooling.elk.kubernetes_collector_enabled
        secret_template_names = sorted(
            set(all_secret_environment_names)
            | (set(_COLLECTOR_SECRET_ENVIRONMENT_NAMES) if collector_enabled else set())
        )
        files = {
            PurePosixPath("deploy", "kubernetes", "base-server.yaml"): (
                self._render_manifest(
                    application_name=application_name,
                    image=profile.image,
                    namespace=profile.namespace,
                    secret_name=profile.secret_name,
                    application_replicas=profile.application_replicas,
                    proxy_replicas=profile.proxy_replicas,
                    durable_job_worker_replicas=profile.durable_job_worker_replicas,
                    log_host_path=profile.log_host_path,
                    secret_environment_names=secret_environment_names,
                    durable_job_worker_secret_environment_names=(
                        durable_job_worker_secret_environment_names
                    ),
                )
            ),
            PurePosixPath("deploy", "kubernetes", "README.md"): self._render_readme(
                application_name=application_name,
                image=profile.image,
                namespace=profile.namespace,
                secret_name=profile.secret_name,
                secret_environment_names=secret_environment_names,
                durable_job_worker_enabled=bool(specification.application.durable_jobs),
                durable_job_worker_replicas=profile.durable_job_worker_replicas,
                collector_enabled=collector_enabled,
                mysql_operator_enabled=profile.mysql_operator.enabled,
                mysql_operator_bootstrap_secret_name=(
                    profile.mysql_operator.bootstrap_secret_name
                ),
                mysql_operator_tls_secret_name=profile.mysql_operator.tls_secret_name,
                mysql_operator_cluster_name=profile.mysql_operator.cluster_name,
                control_plane_enabled=profile.control_plane.enabled,
                control_plane_image=profile.control_plane.image,
                control_plane_secret_name=profile.control_plane.secret_name,
                control_plane_replicas=profile.control_plane.replicas,
            ),
            PurePosixPath("deploy", "kubernetes", "secret.env.example"): "".join(
                f"{environment_name}=\n"
                for environment_name in secret_template_names
            ),
        }
        if profile.mysql_operator.enabled:
            files[PurePosixPath("deploy", "kubernetes", "mysql-operator.yaml")] = (
                self._render_mysql_operator_manifest(
                    application_name=application_name,
                    namespace=profile.namespace,
                    bootstrap_secret_name=profile.mysql_operator.bootstrap_secret_name,
                    tls_secret_name=profile.mysql_operator.tls_secret_name,
                    cluster_name=profile.mysql_operator.cluster_name,
                    mysql_version=profile.mysql_operator.mysql_version,
                    instances=profile.mysql_operator.instances,
                    router_instances=profile.mysql_operator.router_instances,
                    storage_class_name=profile.mysql_operator.storage_class_name,
                    storage_size=profile.mysql_operator.storage_size,
                )
            )
            files[
                PurePosixPath(
                    "deploy", "kubernetes", "mysql-operator-bootstrap.env.example"
                )
            ] = "rootUser=\nrootHost=\nrootPassword=\n"
        if collector_enabled:
            files[PurePosixPath("deploy", "kubernetes", "observability-filebeat.yaml")] = (
                self._render_filebeat_collector_manifest(
                    application_name=application_name,
                    namespace=profile.namespace,
                    secret_name=profile.secret_name,
                    log_host_path=profile.log_host_path,
                    version=specification.tooling.elk.version,
                )
            )
        if profile.control_plane.enabled:
            files[PurePosixPath("deploy", "kubernetes", "control-plane.yaml")] = (
                self._render_control_plane_manifest(
                    application_name=application_name,
                    namespace=profile.namespace,
                    image=profile.control_plane.image,
                    secret_name=profile.control_plane.secret_name,
                    replicas=profile.control_plane.replicas,
                )
            )
            files[
                PurePosixPath(
                    "deploy", "kubernetes", "control-plane-secret.env.example"
                )
            ] = "AUTOFORGE_DATABASE_URL=\nAUTOFORGE_CONTROL_PLANE_TOKEN=\n"
        return files

    def plan(self, specification: ProjectSpec) -> GenerationPlan:
        rendered = self.render(specification)
        spec_hash = specification_hash(specification)
        return GenerationPlan(
            specification_version=specification.spec_version,
            specification_hash=spec_hash,
            files=[
                PlannedFile(
                    relative_path=path,
                    generator_id=self.generator_id,
                    generator_version=self.generator_version,
                    ownership=FileOwnership.GENERATED,
                    action=PlannedAction.CREATE,
                    specification_hash=spec_hash,
                    expected_content_hash=content_hash(content),
                    source="project:kubernetes-base-server",
                )
                for path, content in sorted(rendered.items(), key=lambda item: item[0].as_posix())
            ],
        )

    @staticmethod
    def _kubernetes_name(package_name: str) -> str:
        return package_name.replace("_", "-")

    @staticmethod
    def _secret_environment_names(
        specification: ProjectSpec,
        *,
        target: RuntimeEnvironmentTarget | None = None,
    ) -> list[str]:
        environment_names = {
            environment_name
            for database in specification.application.databases
            for environment_name in (
                database.global_url_env,
                *(shard.url_env for shard in database.shards),
            )
            if environment_name is not None
        }
        for service in specification.application.services:
            environment_names.add(
                KubernetesBaseServerGenerator._service_environment_name(service)
            )
        environment_names.update(
            specification.application.service_token_environments.values()
        )
        environment_names.update(
            environment.name
            for environment in specification.application.runtime_environments
            if target is None or target in environment.targets
        )
        heartbeat = specification.application.control_plane_heartbeat
        if heartbeat.enabled:
            environment_names.update({heartbeat.endpoint_env, heartbeat.token_env})
        environment_names.update(
            specification.tooling.kubernetes.additional_secret_env_names
        )
        return sorted(environment_names)

    @classmethod
    def _durable_job_worker_secret_environment_names(
        cls, specification: ProjectSpec
    ) -> list[str]:
        environment_names = set(
            cls._secret_environment_names(
                specification, target=RuntimeEnvironmentTarget.DURABLE_JOB_WORKER
            )
        )
        environment_names.difference_update(
            specification.application.service_token_environments.values()
        )
        environment_names.difference_update(
            specification.tooling.kubernetes.additional_secret_env_names
        )
        return sorted(environment_names)

    @staticmethod
    def _service_environment_name(service: ServiceSpec) -> str:
        if service.kind == "rabbitmq":
            return service.connection_url_env
        if service.mode == "cluster":
            return service.cluster_url_env
        if service.mode == "sentinel":
            return service.sentinel_urls_env
        return service.url_env

    @staticmethod
    def _render_filebeat_collector_manifest(
        *,
        application_name: str,
        namespace: str,
        secret_name: str,
        log_host_path: str | None,
        version: str,
    ) -> str:
        assert log_host_path is not None
        return f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: {application_name}-filebeat-config
  namespace: {namespace}
data:
  filebeat.yml: |
    filebeat.inputs:
      - type: filestream
        id: {application_name}-application-json
        paths:
          - /var/log/application/*/*.log
        parsers:
          - ndjson:
              target: ""
              add_error_key: true
    fields_under_root: true
    fields:
      autoforge.project: {application_name}
      autoforge.environment: kubernetes
      kubernetes.node.name: ${{NODE_NAME}}
    output.elasticsearch:
      hosts: ["${{ELASTICSEARCH_HOST:?Set ELASTICSEARCH_HOST}}"]
      api_key: "${{ELASTICSEARCH_API_KEY:?Set ELASTICSEARCH_API_KEY}}"
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: {application_name}-filebeat
  namespace: {namespace}
  labels:
    app.kubernetes.io/name: {application_name}
    app.kubernetes.io/component: log-collector
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: {application_name}
      app.kubernetes.io/component: log-collector
  template:
    metadata:
      labels:
        app.kubernetes.io/name: {application_name}
        app.kubernetes.io/component: log-collector
    spec:
      terminationGracePeriodSeconds: 30
      containers:
      - name: filebeat
        image: docker.elastic.co/beats/filebeat:{version}
        imagePullPolicy: IfNotPresent
        args: ["-e", "--strict.perms=false"]
        securityContext:
          runAsUser: 0
          allowPrivilegeEscalation: false
          capabilities:
            drop: ["ALL"]
        env:
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
        - name: ELASTICSEARCH_HOST
          valueFrom:
            secretKeyRef:
              name: {secret_name}
              key: ELASTICSEARCH_HOST
        - name: ELASTICSEARCH_API_KEY
          valueFrom:
            secretKeyRef:
              name: {secret_name}
              key: ELASTICSEARCH_API_KEY
        volumeMounts:
        - name: filebeat-config
          mountPath: /usr/share/filebeat/filebeat.yml
          subPath: filebeat.yml
          readOnly: true
        - name: application-logs
          mountPath: /var/log/application
          readOnly: true
        - name: filebeat-data
          mountPath: /usr/share/filebeat/data
      volumes:
      - name: filebeat-config
        configMap:
          name: {application_name}-filebeat-config
      - name: application-logs
        hostPath:
          path: {log_host_path}
          type: DirectoryOrCreate
      - name: filebeat-data
        hostPath:
          path: {log_host_path}/.filebeat-data
          type: DirectoryOrCreate
"""

    @staticmethod
    def _render_control_plane_manifest(
        *,
        application_name: str,
        namespace: str,
        image: str,
        secret_name: str,
        replicas: int,
    ) -> str:
        return f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {application_name}-control-plane
  namespace: {namespace}
  labels:
    app.kubernetes.io/name: {application_name}
    app.kubernetes.io/component: control-plane
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app.kubernetes.io/name: {application_name}
      app.kubernetes.io/component: control-plane
  template:
    metadata:
      labels:
        app.kubernetes.io/name: {application_name}
        app.kubernetes.io/component: control-plane
    spec:
      containers:
      - name: control-plane
        image: {image}
        imagePullPolicy: IfNotPresent
        ports:
        - name: http
          containerPort: 8000
        env:
        - name: AUTOFORGE_DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: {secret_name}
              key: AUTOFORGE_DATABASE_URL
        - name: AUTOFORGE_CONTROL_PLANE_TOKEN
          valueFrom:
            secretKeyRef:
              name: {secret_name}
              key: AUTOFORGE_CONTROL_PLANE_TOKEN
        readinessProbe:
          httpGet:
            path: /readiness
            port: http
          initialDelaySeconds: 5
          periodSeconds: 5
        livenessProbe:
          httpGet:
            path: /health
            port: http
          initialDelaySeconds: 10
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: {application_name}-control-plane
  namespace: {namespace}
  labels:
    app.kubernetes.io/name: {application_name}
    app.kubernetes.io/component: control-plane
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: {application_name}
    app.kubernetes.io/component: control-plane
  ports:
  - name: http
    port: 8000
    targetPort: http
"""

    @staticmethod
    def _render_manifest(
        *,
        application_name: str,
        image: str,
        namespace: str,
        secret_name: str,
        application_replicas: int,
        proxy_replicas: int,
        durable_job_worker_replicas: int,
        log_host_path: str | None,
        secret_environment_names: list[str],
        durable_job_worker_secret_environment_names: list[str],
    ) -> str:
        application_environment = "".join(
            "        - name: " + environment_name + "\n"
            "          valueFrom:\n"
            "            secretKeyRef:\n"
            f"              name: {secret_name}\n"
            f"              key: {environment_name}\n"
            for environment_name in secret_environment_names
        )
        application_storage = ""
        if log_host_path:
            application_storage = (
                "        volumeMounts:\n"
                "        - name: execution-logs\n"
                "          mountPath: /app/logs\n"
                "      volumes:\n"
                "      - name: execution-logs\n"
                "        hostPath:\n"
                f"          path: {log_host_path}\n"
                "          type: DirectoryOrCreate\n"
            )
        durable_job_worker_manifest = ""
        if durable_job_worker_secret_environment_names:
            durable_job_worker_manifest = (
                KubernetesBaseServerGenerator._render_durable_job_worker_manifest(
                    application_name=application_name,
                    image=image,
                    namespace=namespace,
                    secret_name=secret_name,
                    replicas=durable_job_worker_replicas,
                    secret_environment_names=(
                        durable_job_worker_secret_environment_names
                    ),
                )
            )
        return f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: {application_name}-nginx
  namespace: {namespace}
data:
  default.conf.template: |
    server {{
      listen 80;
      location / {{
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Instance-Name $hostname;
        proxy_pass http://${{UPSTREAM_HOST}}:8000;
      }}
    }}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {application_name}
  namespace: {namespace}
  labels:
    app.kubernetes.io/name: {application_name}
    app.kubernetes.io/component: application
spec:
  replicas: {application_replicas}
  selector:
    matchLabels:
      app.kubernetes.io/name: {application_name}
      app.kubernetes.io/component: application
  template:
    metadata:
      labels:
        app.kubernetes.io/name: {application_name}
        app.kubernetes.io/component: application
    spec:
      containers:
      - name: application
        image: {image}
        imagePullPolicy: IfNotPresent
        ports:
        - name: http
          containerPort: 8000
        env:
        - name: INSTANCE_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: LOG_DIRECTORY
          value: /app/logs
{application_environment}        readinessProbe:
          httpGet:
            path: /readiness
            port: http
          initialDelaySeconds: 3
          periodSeconds: 5
        livenessProbe:
          httpGet:
            path: /health
            port: http
          initialDelaySeconds: 10
          periodSeconds: 10
{application_storage}---
apiVersion: v1
kind: Service
metadata:
  name: {application_name}-backend
  namespace: {namespace}
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: {application_name}
    app.kubernetes.io/component: application
  ports:
  - name: http
    port: 8000
    targetPort: http
---
{durable_job_worker_manifest}apiVersion: apps/v1
kind: Deployment
metadata:
  name: {application_name}-nginx
  namespace: {namespace}
  labels:
    app.kubernetes.io/name: {application_name}
    app.kubernetes.io/component: proxy
spec:
  replicas: {proxy_replicas}
  selector:
    matchLabels:
      app.kubernetes.io/name: {application_name}
      app.kubernetes.io/component: proxy
  template:
    metadata:
      labels:
        app.kubernetes.io/name: {application_name}
        app.kubernetes.io/component: proxy
    spec:
      containers:
      - name: nginx
        image: nginx:1.27-alpine
        ports:
        - name: http
          containerPort: 80
        env:
        - name: UPSTREAM_HOST
          value: {application_name}-backend
        - name: NGINX_ENVSUBST_FILTER
          value: UPSTREAM_HOST
        volumeMounts:
        - name: nginx-template
          mountPath: /etc/nginx/templates/default.conf.template
          subPath: default.conf.template
        readinessProbe:
          httpGet:
            path: /health
            port: http
          initialDelaySeconds: 3
          periodSeconds: 5
        livenessProbe:
          httpGet:
            path: /health
            port: http
          initialDelaySeconds: 10
          periodSeconds: 10
      volumes:
      - name: nginx-template
        configMap:
          name: {application_name}-nginx
---
apiVersion: v1
kind: Service
metadata:
  name: {application_name}-load-balancer
  namespace: {namespace}
spec:
  type: LoadBalancer
  selector:
    app.kubernetes.io/name: {application_name}
    app.kubernetes.io/component: proxy
  ports:
  - name: http
    port: 8080
    targetPort: http
"""

    @staticmethod
    def _render_durable_job_worker_manifest(
        *,
        application_name: str,
        image: str,
        namespace: str,
        secret_name: str,
        replicas: int,
        secret_environment_names: list[str],
    ) -> str:
        environment = "".join(
            "        - name: " + environment_name + "\n"
            "          valueFrom:\n"
            "            secretKeyRef:\n"
            f"              name: {secret_name}\n"
            f"              key: {environment_name}\n"
            for environment_name in secret_environment_names
        )
        rabbitmq_probe = (
            "import asyncio, os, aio_pika; connection = asyncio.run("
            "aio_pika.connect(os.environ['RABBITMQ_URL'], timeout=2)); "
            "asyncio.run(connection.close())"
        )
        return f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {application_name}-durable-job-worker
  namespace: {namespace}
  labels:
    app.kubernetes.io/name: {application_name}
    app.kubernetes.io/component: durable-job-worker
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app.kubernetes.io/name: {application_name}
      app.kubernetes.io/component: durable-job-worker
  template:
    metadata:
      labels:
        app.kubernetes.io/name: {application_name}
        app.kubernetes.io/component: durable-job-worker
    spec:
      containers:
      - name: durable-job-worker
        image: {image}
        imagePullPolicy: IfNotPresent
        command: ["python", "scripts/run_durable_job_worker.py"]
        env:
        - name: INSTANCE_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
{environment}        readinessProbe:
          exec:
            command: ["python", "-c", "{rabbitmq_probe}"]
          initialDelaySeconds: 3
          periodSeconds: 5
        livenessProbe:
          exec:
            command: ["python", "-c", "{rabbitmq_probe}"]
          initialDelaySeconds: 10
          periodSeconds: 10
---
"""

    @staticmethod
    def _render_mysql_operator_manifest(
        *,
        application_name: str,
        namespace: str,
        bootstrap_secret_name: str,
        tls_secret_name: str,
        cluster_name: str,
        mysql_version: str,
        instances: int | None,
        router_instances: int | None,
        storage_class_name: str,
        storage_size: str,
    ) -> str:
        return f"""apiVersion: mysql.oracle.com/v2
kind: InnoDBCluster
metadata:
  name: {cluster_name}
  namespace: {namespace}
  labels:
    app.kubernetes.io/name: {application_name}
    app.kubernetes.io/component: database
spec:
  secretName: {bootstrap_secret_name}
  tlsSecretName: {tls_secret_name}
  tlsCASecretName: {cluster_name}-ca
  instances: {instances}
  version: {mysql_version}
  router:
    instances: {router_instances}
  datadirVolumeClaimTemplate:
    accessModes:
    - ReadWriteOnce
    storageClassName: {storage_class_name}
    resources:
      requests:
        storage: {storage_size}
"""

    @staticmethod
    def _render_readme(
        *,
        application_name: str,
        image: str,
        namespace: str,
        secret_name: str,
        secret_environment_names: list[str],
        durable_job_worker_enabled: bool,
        durable_job_worker_replicas: int,
        collector_enabled: bool,
        mysql_operator_enabled: bool,
        mysql_operator_bootstrap_secret_name: str,
        mysql_operator_tls_secret_name: str,
        mysql_operator_cluster_name: str,
        control_plane_enabled: bool,
        control_plane_image: str,
        control_plane_secret_name: str,
        control_plane_replicas: int,
    ) -> str:
        required_keys = "".join(f"- `{name}`\n" for name in secret_environment_names)
        durable_job_worker_section = (
            f"""
## Durable Job worker

`base-server.yaml` also creates a {durable_job_worker_replicas}-replica internal
Durable Job worker Deployment. It has no Service or public port; it consumes
RabbitMQ events and uses the declared database and worker-targeted environment
keys. Its readiness and liveness probes verify the RabbitMQ connection.
"""
            if durable_job_worker_enabled
            else ""
        )
        durable_job_worker_rollout = (
            f"kubectl rollout status --namespace {namespace} deployment/{application_name}-durable-job-worker\n"
            if durable_job_worker_enabled
            else ""
        )
        collector_section = ""
        if collector_enabled:
            collector_section = f"""
## Filebeat node collector

`observability-filebeat.yaml` creates one Filebeat DaemonSet Pod per eligible
node. It reads only the generated application log hostPath and persists its
registry at `{application_name}`'s `.filebeat-data` directory on that node.

The same Secret must also provide `ELASTICSEARCH_HOST` and
`ELASTICSEARCH_API_KEY`. Use a TLS Elasticsearch endpoint and an API key scoped
only to event publishing. The manifest does not grant Kubernetes API access,
does not create Elasticsearch/Kibana, and does not use privileged mode.

```powershell
kubectl apply --namespace {namespace} -f observability-filebeat.yaml
kubectl rollout status --namespace {namespace} daemonset/{application_name}-filebeat
```

Clusters that prohibit hostPath mounts require an approved node-log collector
policy before this manifest can run.
"""
        mysql_operator_section = ""
        if mysql_operator_enabled:
            mysql_operator_section = f"""
`mysql-operator.yaml` declares an InnoDBCluster for an already-installed MySQL
Operator. Create its separate bootstrap and TLS Secrets before applying it; this
directory does not install the Operator or contain either Secret value.

```powershell
Copy-Item mysql-operator-bootstrap.env.example mysql_operator_bootstrap.env
kubectl create secret generic {mysql_operator_bootstrap_secret_name} --namespace {namespace} --from-env-file=mysql_operator_bootstrap.env
```

`{mysql_operator_tls_secret_name}` must be created outside this directory as a
Kubernetes TLS Secret containing the Operator-approved certificate and key.
`{mysql_operator_cluster_name}-ca` must be a generic
Secret containing `ca.pem` for the same certificate authority.

"""
        else:
            mysql_operator_section = """
This profile does not create database clusters, Routers, or StatefulSets.

"""
        control_plane_section = ""
        if control_plane_enabled:
            control_plane_section = f"""
## Control Plane

`control-plane.yaml` creates a {control_plane_replicas}-replica internal Control
Plane Deployment and a ClusterIP Service. It uses image `{control_plane_image}`
and the separately managed Secret `{control_plane_secret_name}`. The Secret must
provide `AUTOFORGE_DATABASE_URL` and `AUTOFORGE_CONTROL_PLANE_TOKEN`.

```powershell
Copy-Item control-plane-secret.env.example control_plane_secret.env
kubectl create secret generic {control_plane_secret_name} --namespace {namespace} --from-env-file=control_plane_secret.env
kubectl apply --namespace {namespace} -f control-plane.yaml
kubectl rollout status --namespace {namespace} deployment/{application_name}-control-plane
```

The Deployment uses `/health` for liveness and `/readiness` for database-aware
readiness. PostgreSQL and migration execution remain provider-owned; this
manifest does not create a database, migration Job, or public LoadBalancer.
"""
        topology_description = (
            "the Proxy/App topology, a MySQL Operator InnoDBCluster declaration, "
            "and a Control Plane"
            if mysql_operator_enabled and control_plane_enabled
            else "the Proxy/App topology and a MySQL Operator InnoDBCluster declaration"
            if mysql_operator_enabled
            else "the Proxy/App topology and a Control Plane"
            if control_plane_enabled
            else "the Proxy/App topology only"
        )
        return f"""# {application_name} Kubernetes base_server

This directory is generated from `autoforge.yaml`. It creates
{topology_description}; it never contains Secret values and does not apply
itself to a cluster.

## Required runtime contract

- application image: `{image}`
- namespace: `{namespace}`
- Kubernetes Secret: `{secret_name}`
- external entry point: LoadBalancer service on port `8080`

The Secret must provide these keys before the Deployment starts:

{required_keys}Start from the generated zero-value template, fill it locally,
and keep the completed file out of Git:

Database topology is provider-owned. Database URL keys are bound from this
Secret.

{mysql_operator_section}{control_plane_section}```powershell
Copy-Item secret.env.example kis_secret.env
```

Create or rotate the Secret only after filling the values:

```powershell
kubectl create secret generic {secret_name} --namespace {namespace} --from-env-file=kis_secret.env
```

Apply and verify only after the image and Secret are ready:

```powershell
kubectl apply --namespace {namespace} -f base-server.yaml
kubectl rollout status --namespace {namespace} deployment/{application_name}
kubectl rollout status --namespace {namespace} deployment/{application_name}-nginx
{durable_job_worker_rollout}```

`base-server.yaml` uses a local hostPath for `/app/logs` only when the
specification requests one. It is suitable only for single-node local
development (such as Docker Desktop): a hostPath is node-local and cannot
preserve one replica's files when another node runs it. Production deployments
must centralize stdout through a log collector. If a file-retention policy is
also required, use a PVC/PV with an access mode appropriate for the replicas.
{durable_job_worker_section}
{collector_section}""".rstrip() + "\n"
