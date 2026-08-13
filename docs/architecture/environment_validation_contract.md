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

## 생성 산출물과 소유권

Environment Generator의 소유권 경계는 다음과 같다.

```text
generated-owned
  environment/compose.integration.yml
  environment/.env.example
  environment/README.md
  environment/postgres-init/00-databases.sql  # database가 있을 때

user-owned
  environment/compose.override.yml
  .env
  운영 provider별 Secret과 접근 정책
```

`.env.example`에는 변수 이름, 포트, 비밀값이 아닌 예시만 남긴다. 실제 주소,
비밀번호, 토큰, 인증서와 cloud credential은 Git 추적 파일이나 AutoForge manifest에
기록하지 않는다.

## 검증 계약

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
when no hash slots are assigned. If slots already exist, it waits a bounded time
for `cluster_state:ok` with three connected primaries and three connected
replicas; it never issues a second cluster-create command. A topology mismatch
fails clearly instead of silently rebuilding a cluster. A previously unhealthy
local cluster is runtime state, not a reason to reset PostgreSQL, RabbitMQ, or
search data; only its explicitly identified Redis containers and named Redis
volumes may be reset.

1. 같은 명세는 같은 환경 파일과 Content Hash를 생성한다.
2. 비활성화된 환경은 파일을 생성하지 않는다.
3. 선언되지 않은 Service는 Compose에 추가하지 않는다.
4. 생성된 Compose는 서비스 이름과 container port로 내부 통신한다.
5. `.env.example`에는 변수 이름과 비밀값이 아닌 예시만 기록한다.
6. 실제 주소, 비밀번호, token, 인증서와 cloud credential은 생성물과 Manifest에
   기록하지 않는다.
7. 컨테이너 통합 검증은 단위 생성 검증과 분리한다.
