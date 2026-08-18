# AutoForge Control Plane Persistence

- 범위: GenerationJob 상태, idempotent trigger claim, audit envelope

## 목적

Webhook과 worker가 여러 인스턴스로 실행되면 프로세스 메모리는 Job 상태의 원본이
될 수 없다. AutoForge 제어면 PostgreSQL은 다음 상태를 영속화한다.

PostgreSQL은 AutoForge 제어면의 관계형 DB Provider다.

```text
autoforge_generation_jobs
  job_id              Job 식별자
  idempotency_key      외부 요청 중복 방지 키(UNIQUE)
  status               현재 상태
  document             검증된 GenerationJob JSON snapshot
    submission         source/output root 기준 재실행 가능한 상대경로
  revision             성공한 상태 교체 횟수
  lease_owner          현재 worker 식별자
  lease_token          claim마다 바뀌는 fencing token
  lease_expires_at     PostgreSQL 기준 lease 만료 시각
  heartbeat_at         마지막 정상 heartbeat 시각
  created_at/updated_at UTC 시각

autoforge_audit_records
  event_id             Event 식별자이자 중복 방지 PK
  Event 공통 envelope  type/version/time/correlation/causation/job/producer
  payload_redaction    항상 envelope_only
```

Event payload 전체는 audit table에 저장하지 않는다. 명세, token, password와 사용자
코드가 audit 경로로 유출되는 것을 막기 위해 공통 envelope만 저장한다.

## Service heartbeat

`autoforge_service_heartbeats`는 `(service_name, instance_id)`를 primary key로
사용한다. service는 인증된 `POST /v1/service-heartbeats`에 deployed version과 최대
16개의 dependency 상태(`ok`, `degraded`, `unavailable`)만 보낸다. Control Plane은
자신의 TTL 정책과 PostgreSQL `now()`로 `reported_at`과 `expires_at`을 기록하고,
동일 identity 보고를 upsert한다. `GET /v1/service-heartbeats`는 아직 만료되지 않은
보고만 반환한다.

이는 Push 기반 관측 증거이며 Compose/Kubernetes healthcheck, readiness probe 또는
외부 synthetic probe를 대체하지 않는다. Push 보고는 instance identity와 배포 version을
보완하지만, traffic routing과 restart 판단은 계속 Pull probe가 소유한다. 초기 slice는
Control Plane intake와 persistence만 제공하며, generated service reporter, dashboard,
metrics backend와 agent orchestration은 포함하지 않는다.

## 동시성 계약

### Idempotent claim

`create_or_get(job, idempotency_key)`는 PostgreSQL의 unique constraint와
`INSERT ... ON CONFLICT DO NOTHING`을 사용한다. 같은 GitHub delivery 또는 scheduler
요청이 여러 API 인스턴스에 동시에 도착해도 한 Job만 생성되고 나머지는 동일 Job을
조회한다.

### 상태 CAS

`replace(job, expected_status)`는 다음 조건을 한 SQL UPDATE에 포함한다.

```sql
WHERE job_id = :job_id AND status = :expected_status
```

영향받은 row가 정확히 하나가 아니면 `JobConcurrencyError`다. 따라서 같은 pending
Job을 worker 둘이 동시에 generating으로 전이해도 하나만 성공한다. 성공한 교체마다
revision을 1 증가시킨다.

### 실행 lease와 fencing

worker는 pending Job을 `FOR UPDATE SKIP LOCKED` 후보 선택과 조건부 UPDATE로 claim한다.
동일 Job을 동시에 claim해도 하나의 worker만 lease를 받는다. PostgreSQL adapter는
애플리케이션 서버 시계 대신 DB의 `now()`를 기본 기준으로 사용한다.

상태 전이는 expected status뿐 아니라 현재 lease token과 만료 전 조건까지 만족해야
한다. lease가 만료된 뒤 이전 worker가 늦게 결과를 저장해도 새 token과 일치하지 않아
거부된다. heartbeat도 현재 token이 유효하고 아직 만료되지 않은 경우에만 연장된다.

pending Job은 실행을 시작하지 않았으므로 만료 lease takeover를 허용한다. 반면
generating/validating Job의 만료 lease는 다른 Worker가 이어 쓰지 않고
`error=JobLeaseExpired`인 failed 상태로 복구한다. 재시도는 새 격리 Workspace와
새 Job으로 수행한다.

### Audit idempotency

Audit append는 `event_id` primary key에 대해 conflict를 무시한다. 외부 transport의
최소 한 번 전달로 같은 Event가 재전달돼도 audit row는 하나다.

## Trigger와 Status HTTP 계약

```text
POST /v1/generation-jobs
  Authorization: Bearer <control-plane token>
  Idempotency-Key: <1..255 characters>

  project_path         source root 기준 project YAML 상대경로
  specifications_path  source root 기준 module YAML 디렉터리 상대경로
  output_path          output root 기준 생성 Workspace 상대경로

GET /v1/generation-jobs/{job_id}
  Authorization: Bearer <control-plane token>
```

POST는 명세를 검증하고 specification hash가 포함된 pending Job을 영속화한다. 신규
claim은 202, 동일 요청 재전달은 기존 Job과 함께 200을 반환한다. 같은 idempotency
key로 경로 또는 명세 내용이 다른 요청을 보내면 409다. 누락·잘못된 입력은 400/422,
인증 실패는 401, streaming 본문 제한 초과는 413이다.

경로는 절대경로, 드라이브, 역슬래시와 `..`을 허용하지 않는다. 해석한 경로가 symlink
등으로 주입된 source/output root를 벗어나도 거부한다. 본문은 기본 4 KiB이며
`Content-Length`만 신뢰하지 않고 ASGI stream을 읽는 도중 한도를 검사한다.

HTTP 요청은 Generation Pipeline을 직접 실행하지 않는다. 신규 Job일 때만
`GenerationJobCreatedEvent`를 in-process EventBus에 발행하고 즉시 응답한다. 영속
queue 역할은 PostgreSQL pending Job과 lease worker가 담당한다.

## Worker 실행 계약

`GenerationWorker.run_once()`는 pending Job 하나를 claim하고 저장된 submission을
주입된 source/output root 기준 실제 경로로 복원한다. claimed Pipeline은 현재 YAML을
다시 읽고 저장된 unit specification hash와 비교한다. 입력이 사라졌거나 제출 후 명세가
변경됐다면 코드를 만들지 않고 Job을 failed 처리한다.

Pipeline의 generating/validating/terminal 전이는 모두 claim token을 전달한다. worker는
Pipeline과 heartbeat task를 함께 감시한다. heartbeat가 먼저 실패하면 Pipeline을
취소하며, Pipeline이 먼저 끝나면 heartbeat를 취소한다. terminal 상태 저장은 같은
transaction에서 lease 컬럼을 비운다.

Generator 렌더링과 파일 적용은 동기 코드이므로 event loop에서 직접 실행하면
heartbeat가 굶을 수 있다. 출력 규칙은 유지하면서 `asyncio.to_thread()`로 실행해
heartbeat와 cancellation이 계속 스케줄되게 한다.

## Worker 운영 loop와 종료

운영 loop는 Job이 없을 때 설정된 polling 간격 동안 stop event를 기다린다. Job 오류는
구조화된 logging으로 남기고 error backoff 뒤 다음 claim을 계속한다. 시작 시 즉시,
이후 설정 주기마다 abandoned sweep를 실행한다.

SIGINT/SIGTERM adapter는 signal handler에서 Pipeline을 직접 취소하지 않고 thread-safe
방식으로 async stop event만 설정한다. loop는 새 claim을 중단하고 실행 중 Job에는
grace period를 준다. 제한 시간을 넘으면 Pipeline과 heartbeat를 취소하지만 DB lease는
강제로 비우지 않는다. 취소 직후 lease를 지우면 다른 worker가 아직 정리 중인 파일을
동시에 건드릴 수 있기 때문이다. lease가 자연 만료된 뒤 기존 fencing과 abandoned
복구 정책이 소유권을 안전하게 넘긴다.

## Migration과 실행

운영 adapter는 런타임 `create_all()`을 호출하지 않는다. schema는 버전 관리되는
`deploy/postgresql/init/001_control_plane.sql` baseline, `002_job_leases.sql`부터
`006_service_heartbeats.sql`까지 순서로 명시적으로 적용한다. 로컬 통합 구성은
`compose.integration.yaml`을 사용한다.

```powershell
docker compose -p autoforge-control-it -f compose.integration.yaml up -d --wait
$env:AUTOFORGE_TEST_DATABASE_URL = "postgresql+asyncpg://..."
pytest tests/integration/test_postgresql_control_plane.py -q -p no:cacheprovider
```

Compose의 `autoforge_test` 계정과 password는 로컬 통합 테스트 전용이다. 운영 비밀은
파일이나 image에 넣지 않고 배포 환경의 secret provider로 주입해야 한다.

## 패키지 경계

로컬 생성 CLI는 PostgreSQL을 요구하지 않는다. 제어면 서버를 실행할 때만 다음 extra를
설치한다.

```bash
pip install -e ".[server]"
```

PostgreSQL adapter module도 기본 `infrastructure.job` import에서 자동 import하지 않아
server extra가 없는 로컬 CLI의 import를 깨뜨리지 않는다.
