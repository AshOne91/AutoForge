from pathlib import PurePosixPath

from autoforge.core.generation import (
    FileOwnership,
    GenerationPlan,
    PlannedAction,
    PlannedFile,
    content_hash,
    specification_hash,
)
from autoforge.core.specification import ProjectSpec, ServiceSpec

KUBERNETES_BASE_SERVER_GENERATOR_ID = "autoforge.generator.kubernetes-base-server"
KUBERNETES_BASE_SERVER_GENERATOR_VERSION = "0.1.0"


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
        secret_environment_names = self._secret_environment_names(specification)
        return {
            PurePosixPath("deploy", "kubernetes", "base-server.yaml"): (
                self._render_manifest(
                    application_name=application_name,
                    image=profile.image,
                    namespace=profile.namespace,
                    secret_name=profile.secret_name,
                    application_replicas=profile.application_replicas,
                    proxy_replicas=profile.proxy_replicas,
                    log_host_path=profile.log_host_path,
                    secret_environment_names=secret_environment_names,
                )
            ),
            PurePosixPath("deploy", "kubernetes", "README.md"): self._render_readme(
                application_name=application_name,
                image=profile.image,
                namespace=profile.namespace,
                secret_name=profile.secret_name,
                secret_environment_names=secret_environment_names,
            ),
            PurePosixPath("deploy", "kubernetes", "secret.env.example"): "".join(
                f"{environment_name}=\n"
                for environment_name in secret_environment_names
            ),
        }

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
    def _secret_environment_names(specification: ProjectSpec) -> list[str]:
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
    def _render_manifest(
        *,
        application_name: str,
        image: str,
        namespace: str,
        secret_name: str,
        application_replicas: int,
        proxy_replicas: int,
        log_host_path: str | None,
        secret_environment_names: list[str],
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
apiVersion: apps/v1
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
    def _render_readme(
        *,
        application_name: str,
        image: str,
        namespace: str,
        secret_name: str,
        secret_environment_names: list[str],
    ) -> str:
        required_keys = "".join(f"- `{name}`\n" for name in secret_environment_names)
        return f"""# {application_name} Kubernetes base_server

This directory is generated from `autoforge.yaml`. It creates the Proxy/App
topology only; it never contains Secret values and does not apply itself to a
cluster.

## Required runtime contract

- application image: `{image}`
- namespace: `{namespace}`
- Kubernetes Secret: `{secret_name}`
- external entry point: LoadBalancer service on port `8080`

The Secret must provide these keys before the Deployment starts:

{required_keys}Start from the generated zero-value template, fill it locally,
and keep the completed file out of Git:

```powershell
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
```

`base-server.yaml` uses a local hostPath for `/app/logs` only when the
specification requests one. It is suitable only for single-node local
development (such as Docker Desktop): a hostPath is node-local and cannot
preserve one replica's files when another node runs it. Production deployments
must centralize stdout through a log collector. If a file-retention policy is
also required, use a PVC/PV with an access mode appropriate for the replicas.
"""
