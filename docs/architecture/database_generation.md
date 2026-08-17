# Database 생성 아키텍처

## 목적

AutoForge의 Database 기능은 테이블 클래스 몇 개를 출력하는 기능이 아니다.
선언형 명세에서 Domain과 Application이 사용할 저장 계약을 만들고, 선택한 DB
기술의 구현을 Plugin으로 생성하는 기능이다.

## 책임 경계

- **Domain**: 업무 규칙과 상태를 표현하며 FastAPI, ORM과 DB를 알지 않는다.
- **Application**: 유스케이스를 조정하고 Repository Protocol을 호출한다.
- **Packet/API Schema**: HTTP 요청과 응답의 외부 계약이다.
- **Repository Protocol**: Application이 요구하는 저장 기능을 기술 중립적으로
  선언한다.
- **Persistence Adapter**: 선택한 DB 기술로 Repository Protocol을 구현한다.
- **Runtime Topology**: DB 주소, pool, replica, shard와 Secret 참조를 관리한다.

Domain, API Schema와 ORM Model을 하나의 클래스로 강제하지 않는다.

## 분리할 명세

Database 기능을 하나의 거대한 설정 객체로 만들지 않는다.

### Schema Specification

저장할 테이블, 컬럼, 키, 인덱스와 관계를 선언한다.

```yaml
database:
  schemas:
    - name: account
      tables:
        - name: accounts
          fields:
            - name: account_id
              type: integer
              primary_key: true
```

### Repository Specification

Application이 사용할 저장 동작을 선언한다.

```yaml
repositories:
  - name: AccountRepository
    aggregate: Account
    operations:
      - find_by_id
      - save
    queries:
      - name: find_by_email
        column: email
```

`queries`는 로그인처럼 Primary Key가 아닌 고유 식별자로 Aggregate 하나를 찾을 때
사용한다. 조회 대상은 실제 Table에 존재하며 `unique` 또는 Primary Key인 Column만
허용한다. 이를 통해 임의 문자열 operation을 해석하지 않고 명세 검증 단계에서
오타와 다건 조회 위험을 차단한다. 목록·검색·페이지네이션은 별도 계약으로 다룬다.

### Data Placement Specification

데이터가 어느 논리 저장소에 배치되는지 선언한다.

```yaml
placement:
  store: account
  mode: global
  partition_key: account_id
```

`mode`가 `sharded`라면 routing key가 반드시 필요하다. 라우팅에 실패했을 때
Global DB로 조용히 대체하지 않는다.

### Local generated HA mode

`tooling.local_environment.postgres_mode` defaults to `standalone`. When it is
`ha`, generated local Compose keeps the existing application DSN contract
(`postgres:5432`) but places HAProxy at that service name. HAProxy routes writes
only to the Patroni primary; three Spilo PostgreSQL nodes use a three-member etcd
DCS for leader election and streaming replication.

This is a local integration topology, not a multi-host production database
deployment. It intentionally does not add read splitting: Global/Shard routing
chooses the logical database, while PostgreSQL HA chooses the current writer.

### Runtime Database Configuration

환경별 실제 연결 정보는 생성 명세와 분리한다.

```yaml
stores:
  account:
    dsn_secret_ref: ACCOUNT_DATABASE_DSN
    pool_size: 10
```

비밀번호와 토큰은 명세, Manifest, 로그에 기록하지 않는다.

## FastAPI 수명주기

```text
FastAPI lifespan 시작
  → Engine/Pool 생성
  → Repository Adapter 구성

HTTP 요청
  → Dependency
  → Unit of Work 또는 Transaction
  → Application Handler
  → Repository

FastAPI lifespan 종료
  → 역순으로 Adapter와 Engine/Pool 정리
```

Engine과 Pool은 Application 범위이고 Transaction과 Unit of Work는 요청 또는
작업 범위다. 거대한 전역 ServiceContainer는 생성하지 않는다.

## 수평 확장과 샤딩

Global/Shard 분리는 다음 정보를 명시적으로 유지한다.

- 논리 저장소 역할
- 배치 방식
- partition key
- 명시적 routing policy
- shard를 찾지 못했을 때의 오류 정책
- Secret reference

`ShardRouter`는 논리 Store와 Partition Key를 실제 Engine에 연결한다. 등록되지 않은
Global/Shard Engine이나 Routing 실패를 다른 DB로 대체하지 않는다. 물리 Shard
Topology와 DSN은 Runtime Configuration이 소유한다.

## Transaction과 Outbox

하나의 업무 변경과 그 결과 Event를 신뢰성 있게 연결하려면 Outbox가 필요하다.

```text
하나의 DB Transaction
  ├── Aggregate 변경 저장
  └── Outbox Event 저장

별도 Publisher
  → Outbox Event 발행
  → 성공 상태 기록
```

EventBus는 프로세스 내부의 generic event 전달을 담당한다. Outbox와 Message
Transport는 별도 Adapter와 Handler로 연결한다. RabbitMQ Blueprint는 publisher
confirm, durable exchange/queue, manual ACK와 dead-letter topology를 생성한다.
Outbox Relay는 `FOR UPDATE SKIP LOCKED`로 여러 relay의 중복 선점을 막고,
Inbox는 event ID unique claim으로 at-least-once 중복 전달을 안전하게 처리한다.
업무 변경과 Outbox 기록은 반드시 같은 `AsyncSession` transaction에 둔다.

## 생성 파일 소유권

| 출력 | 소유권 | 정책 |
|---|---|---|
| Repository Protocol | GENERATED | 명세에서 재생성 |
| ORM Model | GENERATED | Provider Plugin이 재생성 |
| Persistence Adapter 골격 | SCAFFOLDED | 최초 생성 후 사용자 소유 |
| Alembic 환경 | GENERATED | 프로젝트 명세에서 재생성 |
| Alembic baseline revision | SCAFFOLDED | 최초 생성 후 이력으로 고정 |
| Fake Repository | GENERATED | 테스트용으로 재생성 |
| 업무 규칙 | USER_OWNED | AutoForge가 수정하지 않음 |

## 명세 계약

Database 생성은 다음 명세 모델을 입력으로 사용한다.

- `ColumnSpec`: 기술 중립 Column type, Primary Key, nullable과 default
- `TableSpec`: 중복 Column과 Primary Key 검증
- `RepositorySpec`: Aggregate, Table과 Application operation
- `DataPlacementSpec`: 논리 store, global/sharded mode와 partition key
- `DatabaseSpec`: Table, Repository와 Placement 간 참조 무결성

`ModuleSpec.database`는 선택 항목이다. 기존 Module 명세의 public API는 유지하며
Database가 필요한 Module만 계약을 선언한다.

`DatabaseSpec.provider`는 `agnostic`, `postgresql`, `mysql`을 허용한다.
`agnostic`은 기존 PostgreSQL 호환 baseline을 유지한다. 명시 Provider는 대응하는
raw DDL과 Alembic baseline을 선택하며 Table, Repository, Placement 및
Global/Shard의 이식 가능한 계약은 변경하지 않는다.

## MySQL standalone runtime

`tooling.local_environment.database_provider: mysql` generates one standalone
MySQL service, a named `mysql-data` volume, a `mysql-init` one-shot service, and
`mysql+asyncmy` DSNs with `charset=utf8mb4`. Generated projects also include
`cryptography` because MySQL 8.4's default `caching_sha2_password` authentication
requires RSA password exchange support in the async driver. The init service
waits for MySQL health, creates declared logical databases, and grants the
generated application user access. Generated migrations use the MySQL baseline
and do not reuse PostgreSQL DDL.

`mysql_mode: standalone` is the default local profile. `mysql_mode: ha` is a
MySQL-only opt-in that generates three MySQL 8.4 nodes, a MySQL Shell/AdminAPI
bootstrap job, and a version-matched MySQL Router writer endpoint. Generated
application and migration DSNs use `mysql:6446` in HA mode; the three node
ports remain internal. The generated Router image installs the signed official
MySQL Router 8.4 RPM selected by `MYSQL_ROUTER_VERSION` (default `8.4.8`).
`mysql-init` creates the application account, declared logical databases, and
grants through that writer endpoint.

This is local process-level resilience only: all nodes share one Docker host.
The disposable verifier stops the initial primary, retries an idempotent write
through Router, restarts the node, and waits for the cluster to rejoin. It does
not provide read splitting, cross-provider migration, multi-host durability, or
backups. PostgreSQL-specific RabbitMQ/Outbox/Durable Job generation remains
rejected for this profile.

`mysql_mode` belongs only to `LocalEnvironmentSpec`; it is not a request to
generate Kubernetes database resources. The existing Kubernetes base-server
generator keeps the database provider external and binds declared database URLs
from its named Kubernetes Secret. The first Kubernetes MySQL HA provider is
MySQL Operator for Kubernetes; its decision and ownership boundary are recorded
in [ADR-0002](../adr/0002-kubernetes-mysql-operator-provider.md). Its opt-in
specification profile declares the bootstrap Secret, cluster name, member and
Router counts, TLS Secret, MySQL version, StorageClass, and PVC size. When
enabled, the Kubernetes generator renders an `InnoDBCluster` CR. AutoForge does
not directly emit a MySQL `StatefulSet` or Router Deployment: the installed
Operator reconciles those resources. Operator installation, Secret values,
resource application, backup policy, and restore verification remain operator
responsibilities.

The published `mysql/mysql-router:8.0` image must not be used with MySQL 8.4:
local validation found it classified every member as read-only and closed the
writer route. A generic TCP proxy is not a substitute for the version-matched
Router and InnoDB Cluster contract.

## PostgreSQL DDL Generator

`PostgreSQLDDLGenerator`는 명세의 배치에 따라 다음 결정적 SQL을 생성한다.

```text
database/global/0001_<module>.sql
database/sharded/0001_<module>.sql
```

Global SQL은 Global DB에 한 번 적용하고 Sharded SQL은 모든 Shard DB에 같은
순서로 적용한다. 배치가 없는 테이블은 잘못된 DB로 들어가지 않도록 생성을
거부한다. Shard를 찾지 못한 경우에도 Global DB로 대체하지 않고 오류로 처리한다.

SQL에는 스키마만 저장한다. DSN, 비밀번호, Token과 운영 데이터는 명세나 SQL에
기록하지 않는다. 여러 Application Replica가 동시에 실행할 수 있으므로 Migration은
서버 시작 시 실행하지 않고 전용 로컬 설정 명령이나 CI/CD Job이 적용한다.

## SQLAlchemy async Generator

SQLAlchemy 기능은 Project와 Module Generator로 분리한다.

```text
Project Specification
  → infrastructure/database/base.py
  → infrastructure/database/routing.py
  → infrastructure/database/session.py

Module Specification
  → modules/<module>/generated/sqlalchemy_models.py
```

Project Generator는 하나의 `DeclarativeBase`, `ShardRouter` Protocol과
`AsyncSessionRegistry`를 생성한다. Session은 요청 또는 작업 단위 Transaction을
열며 `expire_on_commit=False`를 사용한다. 등록되지 않은 Global/Shard Engine은
`ShardRoutingError`를 발생시키고 다른 DB로 대체하지 않는다.

Module Generator는 SQLAlchemy 2.x `Mapped`와 `mapped_column` 형식의 Record Model을
생성한다. Pydantic Domain Model과 ORM Record를 같은 클래스로 합치지 않는다.
Repository Adapter가 두 모델 사이를 변환하며 Application은 SQLAlchemy를 직접
참조하지 않는다.

같은 Module Generator는 `sqlalchemy_repositories.py`도 생성한다. Adapter는
`AsyncSession`을 생성하거나 commit하지 않고 생성자 주입으로만 받는다.
`find_by_id`는 Record를 Domain Model로 변환하고 `save`는 Domain Model을 Record로
변환해 `merge`한다. commit과 rollback은 바깥쪽 request/job Transaction이 소유한다.

SQLAlchemy와 asyncpg 의존성은 SQLAlchemy Plugin을 선택한 Project Blueprint가
소유한다. 여러 Generator가 동일한 `pyproject.toml`을 덮어쓰지 않는다.

## Repository Generator

기술 중립 Repository Generator는 `ModuleSpec.database.repositories`에서 다음
GENERATED 파일을 만든다.

```text
modules/<module>/generated/repository.py
modules/<module>/generated/fake_repository.py
```

- Repository Protocol은 Application이 의존할 async method를 선언한다.
- Fake Repository는 메모리 저장소를 사용해 Domain/Application 테스트를 지원한다.
- Primary Key Column type에서 `find_by_id` 인자 type을 결정한다.
- Aggregate Model의 Primary Key field로 Fake 저장 key를 결정한다.
- `find_by_id`, `save`, 고유 Column 단건 조회와 단일 Primary Key를 지원한다.
- SQLAlchemy, Redis와 RabbitMQ 의존성을 포함하지 않는다.

Repository Generator는 FastAPI Module Generator와 같은 Module Plugin Registry에
별도 Plugin으로 등록한다. API 생성과 저장 계약 생성의 책임을 합치지 않는다.

## Runtime database lifespan specification

실제 DSN은 Git에 저장하지 않고 Project 명세에는 환경변수 이름만 선언한다.

```yaml
application:
  databases:
    - name: identity
      global_url_env: IDENTITY_DATABASE_URL
    - name: profile
      shards:
        - shard_id: "1"
          url_env: PROFILE_SHARD_1_DATABASE_URL
```

AutoForge는 서버 프로세스마다 SQLAlchemy async engine pool을 만들고
`AsyncSessionRegistry`를 FastAPI `app.state`에 등록한다. 종료 시 생성 역순으로 모든
engine을 `dispose()`한다. 요청이나 작업은 registry를 주입받아 짧은 transaction
scope를 열며, engine이나 `AsyncSession`을 전역 mutable singleton으로 보관하지 않는다.
Global URL 또는 shard URL이 하나도 없는 store는 명세 오류다. 환경변수가 누락되면
서버 시작을 실패시켜 replica마다 서로 다른 DB fallback이 발생하지 않게 한다.
