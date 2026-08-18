# 환경 실현과 통합 검증 계약

## 목적

AutoForge는 개발자 PC나 운영 환경에 서드파티를 임의로 설치하지 않는다. 대신
프로젝트 명세가 선언한 런타임 의존성을 로컬 개발, 통합 테스트, 운영 환경에서
재현할 수 있는 계약과 산출물로 변환한다.

이는 앱 빌드 전용 Dockerfile 책임을 유지하면서, PostgreSQL, Redis,
RabbitMQ, Airflow가 실제로 연결되는지를 단계적으로 검증하기 위한 계약이다.

## 반드시 분리할 네 가지 범위

| 범위 | 책임 | 예시 |
| --- | --- | --- |
| AutoForge 제어면 | 생성·검증 작업 자체 | JobStore, Git 작업자 |
| 생성 애플리케이션 런타임 | 명세가 선택한 앱 의존성 | PostgreSQL, Redis Session, RabbitMQ |
| 개발·통합 환경 | 재현 가능한 로컬 실행 | Docker Compose, 임시 테스트 DB |
| 운영 환경 | 가용성·보안·비용 결정 | RDS, Redis Cluster, RabbitMQ HA, MWAA |

이 범위는 같은 서비스를 사용하더라도 하나의 설정 파일이나 하나의 Generator로
합치지 않는다. 특히 AutoForge 제어면의 인프라 선택이 생성 애플리케이션의
운영 토폴로지를 결정해서는 안 된다.

## 환경 실현 계약

- `DatabaseStoreSpec`, `ServiceSpec`, `DurableJobSpec`은 애플리케이션의 기능과
  연결 환경변수 계약을 표현한다.
- Dockerfile Generator는 생성 애플리케이션의 빌드만 담당한다.
- Redis Session과 RabbitMQ Outbox는 생성 계약과 단위 테스트가 있다.
- Airflow는 Durable Job `schedule`이 있을 때 DAG 소스와 local runtime을 생성한다.

`tooling.local_environment.enabled`가 참이면 선언된 Database와 Service를 격리된
Docker Compose 환경으로 실현한다. Redis는 standalone 또는 cluster를 지원하며
sentinel을 standalone으로 대체하지 않는다. Durable Job이 있으면 Airflow DAG와
runtime을 포함하고, `application_enabled`가 참이면 migration, FastAPI application,
Outbox relay와 worker를 같은 환경 계약에 연결한다.

이 계약은 로컬·통합 검증 환경만 소유하며 운영 HA 토폴로지를 정의하지 않는다.

`tooling.single_host.enabled`는 별도 Single Host Operating Generator를 선택한다.
이는 `local_environment.enabled`와 `application_enabled`가 만든 dependency runtime을
그대로 재사용하는 Docker Compose overlay이며, Nginx 공개 진입점, 애플리케이션 replica,
restart policy, 그리고 `/app/logs` host bind mount를 추가한다. 따라서 integration
Compose를 운영 배포 모델로 승격하는 것이 아니라, 명시적으로 선택된 generated overlay를
두 파일과 함께 실행한다. 이 첫 slice는 container 장애에 대한 service-level HA만
제공하며 물리 host 장애, TLS, 백업/복구, host bootstrap은 소유하지 않는다.

## 생성 산출물과 소유권

생성된 환경 산출물의 소유권 경계는 다음과 같다.

```text
generated-owned
  environment/compose.integration.yml
  environment/.env.example
  environment/README.md
  environment/postgres-init/00-databases.sql  # database가 있을 때
  deploy/single-host/compose.override.yml    # single_host가 선택될 때
  deploy/single-host/runtime.env.example
  deploy/single-host/nginx/default.conf.template
  deploy/single-host/README.md

user-owned
  environment/compose.override.yml
  .env
  environment/.env
  deploy/single-host/runtime.env
  운영 provider별 Secret과 접근 정책
```

`.env.example`에는 변수 이름, 포트, 비밀값이 아닌 예시만 남긴다. 실제 주소,
비밀번호, 토큰, 인증서와 cloud credential은 Git 추적 파일이나 AutoForge manifest에
기록하지 않는다.

## 검증 계약

## Current local availability boundary

The generated local profile validates restart and recovery of its long-running
services, PostgreSQL leader promotion, Redis Cluster primary promotion, and
MySQL standalone or HA initialization. It does not claim physical-host HA:
every local container shares one Docker host.

## Local MySQL modes

When `tooling.local_environment.database_provider: mysql` is selected, generated
Compose starts MySQL with a named volume and waits for its health check before
the one-shot `mysql-init` service creates declared logical databases and grants
the generated application user access. `migrate` waits for `mysql-init` to exit
successfully. Because one-shot services intentionally finish, operators start
this profile with `docker compose ... up -d` and confirm `mysql-init` exited
with code `0` using `docker compose ps`; `--wait` is not the acceptance signal.

The acceptance boundary is a healthy MySQL service, successful initializer,
application-user connection, and generated MySQL raw DDL applied to a disposable
database. The generated-project acceptance command also builds the generated
image, runs `migrate`, and verifies both its Alembic version and generated table.
When `mysql_mode: ha` is selected, generated Compose creates a three-member
MySQL 8.4 InnoDB Cluster, bootstraps it with MySQL Shell/AdminAPI, installs a
version-matched MySQL Router, and exposes its writer endpoint as `mysql:6446`.
The same acceptance command verifies the generated Router-backed application
account, migration, Alembic version, and generated table. It stops the initial
primary, retries an idempotent write through Router, restarts the node, and
waits for the three-member cluster to return to `OK`. It also starts the
generated application and verifies its `/health` contract before and during the
failover sequence. PostgreSQL-specific RabbitMQ, Outbox, and Durable Job
generation is not supported in this profile.

Optional RAG, MinIO, and ELK overlays use the same service-recovery cadence:
`restart: unless-stopped`, a 10-second healthcheck interval, a 5-second timeout,
and 30 retries. The probe command remains image-native; Qdrant uses a Bash TCP
probe because its image does not contain `curl`, while search, Kibana, and
Filebeat use their available HTTP or native connectivity checks.

When RAG is selected, the generated Windows single-host bootstrap first confirms
the external RAG network, then—after building the generated application image—runs
a read-only request from that image to the configured search `/_cluster/health`
and Ollama `/api/tags` endpoints. A missing endpoint stops bootstrap with an
actionable start-order error; this does not apply to RAG-free profiles and does
not replace the durable worker healthcheck as the readiness authority.

The default `rabbitmq_mode: standalone` profile has one persisted broker. The
opt-in `rabbitmq_mode: cluster` profile emits three RabbitMQ nodes, persistent
node data, a shared `RABBITMQ_ERLANG_COOKIE`, and HAProxy behind the unchanged
`rabbitmq:5672` / `RABBITMQ_URL` client contract. Cluster mode supports the
single declared RabbitMQ service with `queue_type: quorum`, so generated event and
dead-letter queues tolerate one broker-process failure. This is still local
process-level resilience: all containers share one Docker host. Airflow
defaults to one scheduler and one webserver. When
`airflow_scheduler_replicas >= 2` is selected with PostgreSQL HA and Durable
Jobs, the local profile generates indexed schedulers with `LocalExecutor`, a
shared user-owned Fernet key, and independent health checks. Its acceptance
check stops one scheduler, confirms the survivor schedules a Durable Job,
confirms `(job_type, run_key)` creates one Job, then confirms the stopped
scheduler rejoins. Webserver replicas, triggerer HA, remote executors, and
multi-host deployment remain separate deployment contracts.

The RabbitMQ cluster acceptance check is three running broker nodes, quorum
event and dead-letter queues declared by generated messaging code, a successful
publish through HAProxy after one broker is stopped, and that broker rejoining
the cluster. It does not claim multi-host, AZ, or network-partition resilience.

## Local PostgreSQL HA mode

When `tooling.local_environment.postgres_mode: ha` is selected for a project
with database stores, generated Compose adds three etcd members, three Patroni
PostgreSQL nodes, HAProxy at `postgres:5432`, and a one-shot initializer. The
initializer uses the same generated SQL artifact as standalone PostgreSQL for
logical databases, then creates the application login role and assigns database
ownership.

The acceptance check is one leader, two streaming replicas, an application
credential connecting through the writer endpoint, and promotion after stopping
the leader. This is a local Docker integration check, not multi-host or
Kubernetes production HA.

An intentional simultaneous shutdown of all local Patroni nodes is not an
automatic recovery guarantee. Patroni safely avoids choosing an arbitrary
replica when no writable primary remains. Recovering that state requires an
operator-selected manual failover candidate after data assessment; production
orchestration, backup, and restore remain outside this local contract.

## Runtime image and Redis cluster re-entry

Generated Compose services reuse the configured application image tag. After a
consumer source change, an operator must rebuild that image before treating a
container run as evidence for the new source. Recreating only application,
worker, or relay containers does not update their installed package.

The local Redis Cluster initializer is idempotent: it creates a cluster only
when no hash slots are assigned. Redis nodes advertise their Compose service
hostnames to clients. If slots already exist, the initializer resolves each
service's current Compose address and issues `CLUSTER MEET` before it waits a
bounded time for `cluster_state:ok` with three connected primaries and three
connected replicas. This lets the persisted six-node topology rejoin after a
Docker network recreation without a second cluster-create command. A topology
mismatch still fails clearly instead of silently rebuilding a cluster. A
previously unhealthy local cluster is runtime state, not a reason to reset
PostgreSQL, RabbitMQ, or search data; only its explicitly identified Redis
containers and named Redis volumes may be reset.

1. 같은 명세는 같은 환경 파일과 Content Hash를 생성한다.
2. 비활성화된 환경은 파일을 생성하지 않는다.
3. 선언되지 않은 Service는 Compose에 추가하지 않는다.
4. 생성된 Compose는 서비스 이름과 container port로 내부 통신한다.
5. `.env.example`에는 변수 이름과 비밀값이 아닌 예시만 기록한다.
6. 실제 주소, 비밀번호, token, 인증서와 cloud credential은 생성물과 Manifest에
   기록하지 않는다.
7. 컨테이너 통합 검증은 단위 생성 검증과 분리한다.
