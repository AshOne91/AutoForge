# AutoForge Control Plane Persistence

- 확정일: 2026-08-03
- 범위: GenerationJob 상태, idempotent trigger claim, audit envelope

## 목적

Webhook과 worker가 여러 인스턴스로 실행되면 프로세스 메모리는 Job 상태의 원본이
될 수 없다. AutoForge 제어면 PostgreSQL은 다음 상태를 영속화한다.

PostgreSQL은 현재 AutoForge와 생성 대상 서비스의 기본 관계형 DB Provider다.
MySQL 선택 모드는 아직 없으며, 이 제어면 계약을 변경하지 않는 별도 Provider
Plugin은 PostgreSQL 기반 자동화가 안정화된 이후 추가한다.

```text
autoforge_generation_jobs
  job_id              Job 식별자
  idempotency_key      외부 요청 중복 방지 키(UNIQUE)
  status               현재 상태
  document             검증된 GenerationJob JSON snapshot
    submission         source/output root 기준 재실행 가능한 상대경로
  revision             성공한 상태 교체 횟수
  created_at/updated_at UTC 시각

autoforge_audit_records
  event_id             Event 식별자이자 중복 방지 PK
  Event 공통 envelope  type/version/time/correlation/causation/job/producer
  payload_redaction    항상 envelope_only
```

Event payload 전체는 audit table에 저장하지 않는다. 명세, token, password와 사용자
코드가 audit 경로로 유출되는 것을 막기 위해 공통 envelope만 저장한다.

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
queue 역할은 PostgreSQL pending Job과 후속 lease worker가 담당한다.

## Migration과 실행

운영 adapter는 런타임 `create_all()`을 호출하지 않는다. schema는 버전 관리되는
`deploy/postgresql/init/001_control_plane.sql`로 명시적으로 적용한다. 로컬 통합 구성은
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

## 아직 남은 범위

- Job 실행 lease, heartbeat와 abandoned Job 복구
- PostgreSQL Multi-AZ 배포 계약
- backup/restore, 보존 기간과 개인정보 삭제 정책
- Metrics projection
