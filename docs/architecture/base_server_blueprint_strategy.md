# base_server 수준의 생성 Blueprint 전략

## 목적

AutoForge의 목표는 `base_server`를 그대로 복제하거나 AutoForge 자신을 웹서비스로
바꾸는 것이 아니다. 하나의 검증 가능한 명세에서 `base_server`급 FastAPI 서버의 공통
구조를 반복 생성하고, 개발자는 생성 경계 밖의 도메인 업무만 구현하게 만드는 것이다.

`kis-auto-trading`은 이 목표를 검증하는 첫 번째 소비자다.

```text
Project/Application/Module 명세
  -> FastAPI 프로젝트와 Module 조합
  -> DB, Redis, Queue, Worker, Scheduler, observability 산출물
  -> Docker/Compose/Kubernetes 실행 산출물
  -> 검증, Git automation, 배포 자동화
```

## 역할 분리

| 대상 | 책임 |
| --- | --- |
| `base_server` | 수작업으로 구현된 기능·운영 구조의 참조 모델 |
| AutoForge | 명세, 생성, ownership, 검증, Git automation 플랫폼 |
| `kis-auto-trading` | 생성된 구조가 실제 제품 요구에서 유효한지 검증하는 소비자 |

따라서 `base_server`의 개별 Router나 전역 ServiceContainer를 복사하지 않는다. 그
프로젝트가 보여 주는 중요한 원리는 Application이 필요한 Module과 Service를 선택해
조합하는 Composition Root라는 점이다.

## base_server에서 계승할 범위

`base_server`는 FastAPI Router, Global/Sharded database, Redis session/cache,
Queue/Outbox, scheduler, distributed lock, WebSocket, 외부 API, 파일 로그,
환경별 설정, Docker 역할 분리를 한 Application에 조합한다.

AutoForge는 이를 다음처럼 현대화한다.

| 참조 구현 | AutoForge 방향 |
| --- | --- |
| 정적 ServiceContainer와 전역 상태 | lifespan과 명시적 dependency provider |
| 수작업 Template/Router 조립 | 결정적 Module/Application generation |
| JSON 설정과 수동 SQL | 검증 가능한 Spec, DDL, Alembic, Manifest |
| 특정 MySQL/AWS 구현 결합 | provider/adapter 경계와 소비자 선택 |
| 단일 서버 초기화 흐름 | app, worker, scheduler 역할별 실행 산출물 |
| 수동 Compose/Kubernetes | 선택형 generator와 재현 가능한 검증 |

## 현재 완료된 기반

AutoForge에는 다음 계약이 구현·검증돼 있다.

- Project/Module 명세, GENERATED/SCAFFOLDED/USER_OWNED ownership, Manifest
- FastAPI 프로젝트·모듈·모델·Router·Handler scaffold
- PostgreSQL DDL/Alembic과 Global/Shard placement
- Redis Session, RabbitMQ, Transactional Outbox
- Durable Job, Airflow DAG, Outbox relay, worker
- Dockerfile, local Compose, ELK profile, base-server형 Kubernetes base manifest
- EventBus/Pipeline, Control Plane, GitHub webhook, generation worker와 Git automation
- 구조화 로그, Audit, envelope-only Metrics sink contract

KIS Compose 검증에서는 PostgreSQL, Redis Cluster, RabbitMQ, migration,
application, Airflow, Outbox relay, durable-job worker가 실제로 기동됐다. Durable
Job은 `requested`에서 terminal `failed` 상태까지 전이됐다. 이는 사용자 소유 업무
handler가 아직 미구현이기 때문이며 인프라 계약 실패가 아니다.

2026-08-11에는 같은 Compose application에서 `signup -> login -> Redis session ->
sharded profile update/read` HTTP 경로도 성공했다. Identity와 Profile handler는
KIS의 SCAFFOLDED 사용자 소유 코드이고, session store·router·persistence는
AutoForge 생성 산출물이다. 이 경계가 첫 Blueprint의 실제 기준 사례다.

## 현재 공백

가장 큰 공백은 Router 개수가 아니라 **Application Blueprint**다. 현재 Module은
독립적으로 생성되지만, 어떤 공통 서비스·수명주기·데이터 배치·transport가 하나의
Application 기능 묶음을 이루는지 선언하고 조합하는 재사용 계약은 아직 없다.

| 범주 | 상태 | 다음 책임 |
| --- | --- | --- |
| Application Blueprint 조합 | 미구현 | Module, Service, lifecycle, placement를 한 기능 단위로 선언 |
| Identity/Session/Profile | KIS 수직 기능 검증 | 공통 조합 계약 추출, credential policy는 사용자 소유 유지 |
| Market ingestion | Durable Job 기반 완료 | 외부 API adapter와 KIS 업무 handler |
| WebSocket/Notification | 미구현 | 연결 lifecycle, Redis shared state, Queue contract |
| Observability backend | contract 완료 | OpenTelemetry/Prometheus 또는 선택 backend adapter |
| 운영 Kubernetes | base manifest 완료 | Ingress/TLS/HPA/PDB/PVC와 실제 cluster 검증 |
| artifact publish/deploy | 미구현 | image publishing과 deployment plugin |

## 성숙도 해석

다음 수치는 테스트 개수가 아닌 목표 대비 구조 성숙도 추정이다.

- AutoForge 생성·검증·자동화 기반: 약 60~65%
- base_server급 공통 웹서버를 생성할 능력: 약 35~40%
- KIS의 실제 자동매매 업무: 약 15~20%

기반 점수가 더 높은 이유는 명세, ownership, persistence, worker, local runtime이
이미 검증됐기 때문이다. 최종 제품 점수가 낮은 이유는 재사용 Application Blueprint와
소비자 도메인 업무가 아직 완성되지 않았기 때문이다.

## 구현 순서

### 1. Application Blueprint 계약

첫 Blueprint는 KIS가 이미 검증한 `identity + session + sharded profile`에서
추출해야 한다. 이 계약은 다음을 실제 생성 산출물에 반영할 때만 추가한다.

- Global Identity store와 Sharded Profile store
- Redis session dependency와 current-user routing
- 명시적인 lifecycle/dependency wiring
- GENERATED Router/Schema/Persistence와 SCAFFOLDED business handler 경계

명세 필드만 추가하고 generator가 사용하지 않는 추상화는 만들지 않는다.

### 2. Identity + Session + Profile 수직 기능

현재 KIS는 password hashing, token/session validation, shard selection, profile
persistence를 end-to-end로 검증했다. 다음 AutoForge 작업은 이를 generic handler로
복사하는 것이 아니라, 생성되는 Router/session/persistence와 SCAFFOLDED credential
policy/business handler의 조합 계약을 추출하는 것이다. credential handling은 보안
경계이므로 소비자 요구와 함께 설계한다.

2026-08-11 기준으로 이 조합은 기존 Pipeline에서 이미 실제 실행된다. Pipeline은
`autoforge.yaml`의 `application.modules`와 `specifications/*.yaml`의 선언 일치를
검증한 뒤 Project unit과 모든 Module unit을 함께 생성한다. 이를 바로 소비하는
`blueprints/identity_session_profile` 입력 Blueprint를 제공한다. 이는 새로운
metadata 전용 `BlueprintSpec`이 아니라, 기존 `autoforge generate` 명령으로 Router,
schema, Global/Shard persistence, Redis session contract를 생성하는 실제 입력이다.
생성되는 `handlers.py`는 SCAFFOLDED이고 credential·token·shard-selection 정책은
소비자가 구현한다.

같은 날짜에 이 Blueprint는 별도 Docker Compose 프로젝트에서 실제로 검증됐다.
생성 Dockerfile build, PostgreSQL, Redis Cluster, migration, FastAPI application이
순서대로 healthy가 되었고 `/health`는 `{"status":"ok"}`을 반환했다. 이 검증은
일반 application profile이며 RabbitMQ, Airflow, durable job worker는 포함하지 않는다.
그 서비스들은 소비자가 durable-job 조합을 선언할 때 기존 통합 profile로 추가한다.

### 3. Market ingestion Blueprint

외부 API adapter, cache, durable job, Airflow, Outbox/Worker를 조합한다. AutoForge는
공통 실행 경계를 생성하고 뉴스 수집·매매 전략 같은 업무는 KIS가 소유한다.

`blueprints/scheduled_ingestion`은 이 단계의 실행 기반을 먼저 제공한다. 이는
durable-job store, RabbitMQ/Outbox, Airflow, worker, Docker Compose까지만 생성한다.
외부 API adapter와 실제 ingestion handler는 SCAFFOLDED 소비자 코드로 남긴다.

### 4. Realtime Blueprint

WebSocket, notification, connection lifecycle, Redis shared state, Queue delivery를
하나의 기능 묶음으로 선언·생성·검증한다.

### 5. 운영 Blueprint

로그/trace/metric backend adapter, Nginx/Ingress, TLS, HPA, PDB, PVC, image publishing,
deployment plugin을 실제 Kubernetes 검증과 함께 추가한다.

## 완료 기준

base_server급 생성 목표는 다음을 만족할 때 달성으로 본다.

1. 소비자가 공통 Blueprint를 선택하면 연결된 Router, dependency, persistence,
   worker, runtime 산출물이 함께 생성된다.
2. Global/Shard, Redis, Queue, Durable Job의 책임 경계가 명세와 runtime에서 동일하다.
3. 생성 파일과 사용자 업무 handler의 ownership이 재생성 후에도 보존된다.
4. local Compose와 Kubernetes 선택 profile에서 app/worker/scheduler가 재현 가능하다.
5. KIS가 최소한 identity/session/profile과 하나의 scheduled market ingestion을
   성공 경로까지 실제로 검증한다.

## 금지 사항

- `base_server`의 전역 singleton과 거대한 startup 흐름을 복제하지 않는다.
- 13개 Router를 한 번에 generator 기능으로 만들지 않는다.
- 실제 소비자가 없는 cloud, broker, database provider를 먼저 추가하지 않는다.
- 사용자 소유 KIS 전략·뉴스 수집·주문 업무를 AutoForge generator에 넣지 않는다.
