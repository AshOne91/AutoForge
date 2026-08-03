# Database 생성 아키텍처

## 목적

AutoForge의 Database 기능은 테이블 클래스 몇 개를 출력하는 기능이 아니다.
선언형 명세에서 Domain과 Application이 사용할 저장 계약을 만들고, 선택한 DB
기술의 구현을 Plugin으로 생성하는 기능이다.

이 문서는 `common-tool`, `game-server`, SKN12 `base_server`에서 확인한 구조를
AutoForge와 실제 적용 프로젝트인 `kis-auto-trading`에 어떻게 반영할지 정한다.

## 참고 프로젝트별 역할

| 참고 프로젝트 | 재사용할 지식 | 그대로 복사하지 않을 부분 |
|---|---|---|
| `common-tool` | Packet, Model, DBTable, Load/Save 코드와 SQL을 명세에서 생성하는 방식 | C# 전용 출력, 저장 프로시저 강제, 강한 결합 |
| `game-server` | Global/Game/Log DB 역할 분리, 사용자 기준 DB 배치, 수평 확장 | 고정 서버 ID, 로컬 스레드 모델, MySQL 전용 규칙 |
| SKN12 `base_server` | FastAPI lifespan, async DB pool, Global/Shard 연결, Outbox의 필요성 | 전역 ServiceContainer, 세션 내부에 숨은 라우팅, Global DB 자동 fallback |
| `kis-auto-trading` | 실제 거래 서비스 요구사항과 생성 결과 검증 | 프로젝트 고유 투자 전략을 범용 Generator에 포함 |

전체 참고 프로젝트 적용 기준은 `reference_project_strategy.md`를 따른다.

## 두 저장소의 책임

```text
AutoForge
  ├── DatabaseSpec와 DataPlacementSpec
  ├── Repository Protocol Generator
  ├── ORM/DDL/Migration Plugin
  ├── 생성 파일 소유권과 Manifest
  └── 생성 결과 검증

kis-auto-trading
  ├── 실제 Project/Module/Database 명세
  ├── 생성된 FastAPI 서버 골격
  ├── 사람이 작성하는 거래 업무 규칙
  ├── KIS API Adapter
  └── 운영 환경 설정과 Secret 참조
```

AutoForge 기능은 실제 프로젝트에 적용하여 검증한다. 반대로
`kis-auto-trading`에서 반복되는 골격을 먼저 손으로 늘린 뒤 AutoForge가 따라가게
하지 않는다.

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

## Redis와 RabbitMQ 경계

Redis와 RabbitMQ는 `kis-auto-trading`의 필수 Service다.

- Redis는 cache, TTL 상태, rate limit, idempotency와 분산 coordination을 담당한다.
- RabbitMQ는 비동기 작업, ACK/NACK, retry, DLQ와 Worker 분산을 담당한다.
- 관계형 DB는 업무 데이터의 원장이다.
- Outbox는 DB 변경과 RabbitMQ 발행 사이의 신뢰성을 보완한다.
- AutoForge EventBus는 프로세스 내부 이벤트 전달만 담당한다.

Redis에 자체 Queue를 다시 구현하거나 RabbitMQ에 cache 책임을 넣지 않는다.

## 수평 확장과 샤딩

`game-server`와 SKN12 `base_server`에서 확인한 Global/Shard 구분은 유지한다.
다만 첫 Database MVP에서는 샤드 실행 코드를 구현하지 않는다.

먼저 명세가 다음 정보를 잃지 않도록 경계를 확보한다.

- 논리 저장소 역할
- 배치 방식
- partition key
- 명시적 routing policy
- shard를 찾지 못했을 때의 오류 정책
- Secret reference

샤드 catalog, replica 선택, failover와 재배치는 후속 Runtime Plugin이 담당한다.

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
| Migration | SCAFFOLDED | 생성 후 이력으로 고정 |
| Fake Repository | GENERATED | 테스트용으로 재생성 |
| 업무 규칙 | USER_OWNED | AutoForge가 수정하지 않음 |

## 첫 수직 검증 대상

첫 실제 검증 대상은 `kis-auto-trading`의 `account` Module이다.

```text
Account API Schema
  → Account Application Handler
  → Account Domain Model
  → AccountRepository Protocol
  → Fake Repository
```

그다음 SQLAlchemy/Alembic Plugin을 추가하여 같은 Repository Protocol의 실제
Adapter를 생성한다. 이 순서로 기술 중립 계약을 먼저 검증한다.

## 현재 구현된 최소 계약

첫 수직 검증을 위해 다음 명세 모델을 구현했다.

- `ColumnSpec`: 기술 중립 Column type, Primary Key, nullable과 default
- `TableSpec`: 중복 Column과 Primary Key 검증
- `RepositorySpec`: Aggregate, Table과 Application operation
- `DataPlacementSpec`: 논리 store, global/sharded mode와 partition key
- `DatabaseSpec`: Table, Repository와 Placement 간 참조 무결성

`ModuleSpec.database`는 선택 항목이다. 기존 Module 명세의 public API는 유지하며
Database가 필요한 Module만 계약을 선언한다.

첫 실제 명세는 `C:\kis-auto-trading\specifications\identity.yaml`과
`account.yaml`이다. 로그인 인증정보는 Global, 개인정보 Profile은 `user_id`를
partition key로 사용하는 Sharded 배치로 검증한다.

이 단계의 `provider`는 `agnostic`만 허용한다. SQLAlchemy, Alembic과 실제 DB
접속은 후속 Plugin에서 구현한다.

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

같은 Module Generator는 `sqlalchemy_repositories.py`도 생성한다. Adapter는
`AsyncSession`을 생성하거나 commit하지 않고 생성자 주입으로만 받는다.
`find_by_id`는 Record를 Domain Model로 변환하고 `save`는 Domain Model을 Record로
변환해 `merge`한다. commit과 rollback은 바깥쪽 request/job Transaction이 소유한다.

SQLAlchemy와 asyncpg 의존성은 SQLAlchemy Plugin을 선택한 Project Blueprint가
소유한다. 여러 Generator가 동일한 `pyproject.toml`을 덮어쓰지 않는다.

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
- 첫 구현은 `find_by_id`, `save`, 고유 Column 단건 조회와 단일 Primary Key만 지원한다.
- SQLAlchemy, Redis와 RabbitMQ 의존성을 포함하지 않는다.

Repository Generator는 FastAPI Module Generator와 같은 Module Plugin Registry에
별도 Plugin으로 등록한다. API 생성과 저장 계약 생성의 책임을 합치지 않는다.

`C:\kis-auto-trading\specifications\account.yaml`에서
`UserProfileRepository`와 `FakeUserProfileRepository` 출력의 Python 문법을
실제로 검증했다.

## 현재 구현된 최소 계약

첫 수직 검증을 위해 다음 명세 모델을 구현했다.

- `ColumnSpec`: 기술 중립 Column type, Primary Key, nullable과 default
- `TableSpec`: 중복 Column과 Primary Key 검증
- `RepositorySpec`: Aggregate, Table과 Application operation
- `DataPlacementSpec`: 논리 store, global/sharded mode와 partition key
- `DatabaseSpec`: Table, Repository와 Placement 간 참조 무결성

`ModuleSpec.database`는 선택 항목이다. 기존 Module 명세의 public API는 유지하며
Database가 필요한 Module만 계약을 선언한다.

첫 실제 명세는 `C:\kis-auto-trading\specifications\account.yaml`이며
UserProfile Model, API, Repository와 global placement를 함께 검증한다.

이 단계의 `provider`는 `agnostic`만 허용한다. SQLAlchemy, Alembic과 실제 DB
접속은 후속 Plugin에서 구현한다.

## 첫 구현에서 제외

- 실제 DB 접속
- 자동 shard 증설과 재배치
- replica failover
- 분산 Transaction
- Outbox Publisher
- Kubernetes 배포 자동화
- Git commit, push, pull request

이 기능들은 계약과 생성 결과가 실제 프로젝트에서 검증된 후 별도로 구현한다.
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
