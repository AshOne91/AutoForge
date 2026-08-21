# AutoForge Quest: 오늘의 퀘스트 보드 서버 만들기

> 문서 역할: GUIDE
>
> 이 문서는 [처음부터 만드는 로그인 서버](login_server_from_zero.md)를 끝낸 뒤 읽는다.
> 현재 AutoForge가 생성할 수 있는 공통 서비스를 **왜 선택하는지**, **어떻게 도메인에
> 연결하는지**, **무엇을 확인해야 하는지** 실습 순서로 설명한다. 이 문서는 서비스의
> API 계약을 새로 정의하지 않는다. 정확한 명세 필드는 [명세 설계](../architecture/specification_design.md),
> 생성·수정 경계는 [생성 계약](../architecture/generation_contract.md)이 정본이다.

## 0. 이 문서는 작은 게임을 만드는 실습이다

첫 가이드에서 만든 회원가입·로그인 서버 다음에, 플레이어가 오늘의 퀘스트를 확인하고
완료 보상을 받는 **Quest Board**를 조금씩 만든다. 실제 게임을 완성하는 것이 아니라,
각 공통 서비스가 어느 순간 필요해지는지를 재미있는 한 문장으로 연결하는 것이 목표다.

각 Level은 항상 같은 네 가지 질문에 답한다.

| 순서 | 확인할 것 |
| --- | --- |
| 미션 | 플레이어에게 어떤 일이 일어나는가? |
| AutoForge | YAML을 통해 어떤 공통 코드·Compose·SQL을 생성하는가? |
| 내 코드 | `handlers.py`에서 어떤 업무 규칙만 작성하는가? |
| 클리어 조건 | Docker, HTTP, 로그에서 무엇이 보여야 하는가? |

한 Level을 클리어하기 전 다음 Level의 YAML을 복사하지 않는다. 그렇게 해야 실패했을 때
어느 서비스가 원인인지 바로 알 수 있다.

여기서 말하는 **도메인**은 `프로필`, `주문`, `알림`처럼 사용자가 이해하는 업무 단위다.
**공통 서비스**는 Redis·PostgreSQL·RabbitMQ처럼 여러 도메인이 함께 쓰는 기술 기반이다.
AutoForge는 둘을 섞어 직접 구현하게 하지 않는다. YAML에서 필요한 서비스를 선택하면
연결 코드와 운영 파일을 만들고, 여러분은 handler에 도메인 규칙을 작성한다.

첫 번째 퀘스트는 `내 플레이어 카드`다. PostgreSQL, Redis session, 요청 재실행 방지만
선택한다. 이미지·외부 계정·비용이 필요한 RabbitMQ, 검색, LLM, SMS는 퀘스트 요구가
생겼을 때 해금한다. 이것은 기능을 빼는 것이 아니라, 작은 서버가 실제로 동작한다는
확인을 먼저 끝내는 순서다.

```text
브라우저
  └─ Bearer access token
       └─ FastAPI Router (GENERATED)
            ├─ Redis SessionStore: "누가 요청했는가?"
            ├─ RequestReplayStore: "같은 수정 요청인가?"
            └─ SCAFFOLDED handler
                 └─ PostgreSQL Repository: "플레이어 카드를 저장/조회"
```

완료 후 다음을 직접 확인한다.

- 로그인하지 않은 요청은 `401`이다.
- 로그인한 플레이어는 자기 카드만 읽고 수정한다.
- 같은 `Idempotency-Key`와 같은 본문을 두 번 보내도 첫 결과가 재사용된다.
- 같은 키에 다른 본문을 보내면 `409`로 거부된다.

여기서 중요한 점은 **서비스를 전부 켜는 것이 목표가 아니라**, 도메인에 필요한
서비스만 명세에 선언하는 것이다. 플레이어 카드의 이름 한 줄을 저장하는 데 RabbitMQ, LLM,
검색 엔진을 설치하면 오히려 운영할 것이 늘어난다.

## Level 0. 모험 시작 전 체크

다음을 먼저 완료한다.

1. [로그인 서버 가이드](login_server_from_zero.md)의 1~13절을 한 번 실행했다.
2. `python -m autoforge.main version`이 동작한다.
3. Docker Desktop이 실행 중이다.
4. 기존 `login-server`를 유지하고 싶다면 이 실습은 별도 폴더·별도 포트에서 실행한다.

이 문서에서 사용할 경로는 다음과 같다.

```text
C:\workspace\login-server-spec       # 첫 가이드에서 만든 명세
C:\workspace\profile-server-spec     # 이번 실습의 복사본 명세
C:\workspace\profile-server          # 이번 실습의 별도 생성 결과
```

별도 `package_name`과 `49200` 포트 블록을 쓰므로, 첫 로그인 서버를 끄거나 기존
PostgreSQL volume을 지울 필요가 없다.

## Quest Map. AutoForge 능력 해금 지도

아래 표는 현재 생성 가능한 공통 서비스 전체를 사용 시점별로 정리한 것이다. `선택`은
명세의 위치이고, `첫 도메인 예시`는 그 서비스가 실제로 필요한 순간이다.

| 범주 | 선택 | 왜 존재하는가 | 첫 도메인 예시 | 지금 필요한가 |
| --- | --- | --- | --- | --- |
| 관계형 DB | `application.databases` + module `database` | 원장 데이터·unique 제약·transaction | 계정, 프로필, 주문 | 예 |
| Redis 세션 | `application.services.kind: redis_session` | 로그인 상태를 빠르게 조회·폐기 | 로그인, 로그아웃, 권한 | 예 |
| 요청 재실행 방지 | endpoint `idempotency: true` | 재시도/더블 클릭이 같은 쓰기를 두 번 만들지 않게 함 | 프로필 수정, 결제 요청 | 예 |
| RabbitMQ + Outbox/Inbox | `application.services.kind: rabbitmq` | DB 변경 뒤 비동기 후속 작업을 신뢰성 있게 전달 | 가입 환영 메일, 주문 후 알림 | 아직 아님 |
| Durable Job + Airflow | `application.durable_jobs`의 `schedule` | 요청과 분리된 예약·장기 작업 | 뉴스 수집, 일 배치 | 아직 아님 |
| Key-Value Store | `tooling.key_value_store` | Redis/Memcached를 기술 중립 TTL cache로 사용 | 시세·프로필 조회 cache | 읽기 병목 뒤 |
| Distributed Lock | `tooling.distributed_lock` | 여러 replica가 같은 작업을 동시에 수행하지 않게 함 | 한 사용자당 한 번만 실행할 정산 | 동시 실행이 실제로 생긴 뒤 |
| Object Storage | `tooling.storage` | 파일을 DB 행에 넣지 않고 S3 호환 저장소에 보관 | 프로필 사진, 원본 문서 | 사진 기능 뒤 |
| External Provider | `tooling.external_provider` | 외부 HTTP API를 async 경계와 fake로 감쌈 | 결제·증권·환율 API | 외부 API 연결 직전 |
| Search | `tooling.search` | Elasticsearch/OpenSearch의 keyword 검색 경계 | 공지·뉴스 검색 | 검색 화면 뒤 |
| Vector Store | `tooling.vector_store` | Qdrant의 embedding/vector 조회 경계 | 유사 문서 검색 | embedding 목표가 생긴 뒤 |
| RAG overlay | `tooling.rag` | local Search + Qdrant + Ollama 인프라 묶음 | 문서 질의응답 | 검색·AI 둘 다 필요할 때 |
| Realtime | `tooling.realtime` | WebSocket hub와 선택적 Redis Pub/Sub backplane | 알림 badge, 채팅 힌트 | HTTP 흐름 안정 뒤 |
| Webhook 알림 | `tooling.notification` | 외부 webhook으로 한 건 전달 | Discord/Slack 운영 알림 | 수신 endpoint가 정해진 뒤 |
| Email | `tooling.email` | SMTP 전송 경계와 fake | 비밀번호 재설정 메일 | 메일 provider 선정 뒤 |
| SMS | `tooling.sms` | SOLAPI SMS 전송 경계와 fake | 2차 인증 문자 | SMS 발신 번호 준비 뒤 |
| LLM | `tooling.llm` | OpenAI Responses API 경계와 fake | 문서 요약, AI 보조 | 모델·비용 정책 뒤 |
| Control Plane heartbeat | `application.control_plane_heartbeat` | 생성 실행 단위의 상태 보고 경계 | worker/API 운영 상태 보고 | Control Plane을 실제로 쓸 때 |
| 내부 서비스 인증 | `application.service_tokens` + endpoint `service_token` | 내부 호출자를 fail-closed로 구분 | worker → internal API | 별도 실행 단위를 연결할 때 |
| ELK | `tooling.elk` | JSON 로그 파일 수집·검색 | 장애 원인 추적 | HTTP 도메인 안정 뒤 |
| Docker/Local Environment | `tooling.docker`, `tooling.local_environment` | 재현 가능한 이미지·Compose·healthcheck | 모든 로컬 실습 | 예 |
| 단일 호스트 HA | `tooling.single_host` | 한 물리 PC에서 replica·복구를 검증 | 로그인 API scale-out | 단일 모드 통과 뒤 |
| Kubernetes | `tooling.kubernetes` | provider가 정해진 뒤 배포 명세 생성 | 실제 다중 노드 배포 | 로컬 검증 뒤 |

`Storage`는 기본적으로 MinIO overlay 파일을 생성하지만, 애플리케이션에서 S3
경계를 쓸 때만 `runtime_enabled: true`를 추가한다. 반대로 Search/Vector/LLM처럼
외부 주소나 credential이 필요한 서비스는 명세만 켠다고 진짜 provider에 연결되지
않는다. `.env` 또는 Secret에 실제 주소와 비밀값을 주입한 뒤에만 연결한다.

### 레벨 진행표: 모든 AutoForge 능력을 한 서버에 연결하기

아래 순서는 **모두 한꺼번에 설치하라는 목록이 아니다.** 앞 Level의 클리어 조건이
통과된 뒤 다음 Level 하나만 선택한다. 각 Level의 YAML과 실행 명령은 뒤 절에 있고,
도메인 코드에는 선택된 서비스의 generated protocol만 들어간다.

| Level | Quest Board에서 생긴 요구 | 함께 배우는 AutoForge 기능 | 클리어 조건 |
| --- | --- | --- | --- |
| 0 | 대장간을 안전하게 연다 | YAML 명세, Blueprint, 검증, generation plan, Manifest, 파일 소유권 | `generate`가 성공하고 `generated` 파일을 건드리지 않는다 |
| 1 | 플레이어 카드를 저장한다 | PostgreSQL, SQL/Alembic, Redis session, idempotency, Docker, 로그 | 로그인·카드 수정·동일 요청 replay·`409`를 확인한다 |
| 2 | 보상 지급을 기다리지 않고 전달한다 | RabbitMQ, Transactional Outbox, Inbox, worker | DB 변경과 보상 event가 분리되어 전달된다 |
| 3 | 매일 새 퀘스트를 연다 | Durable Job, Airflow scheduler | HTTP 요청 없이도 정해진 시간에 job이 실행된다 |
| 4 | 인기 퀘스트를 빠르게 보여 준다 | Redis/Memcached cache, Distributed Lock | replica 수와 무관하게 cache/lock 계약을 쓴다 |
| 5 | 뱃지 이미지를 보관한다 | S3 protocol, MinIO local overlay | DB에는 object key만, 파일은 object storage에 남는다 |
| 6 | NPC에게 외부 정보를 묻는다 | External Provider, deterministic fake | fake 테스트 후 실제 URL/Secret을 주입한다 |
| 7 | 퀘스트 도감을 찾고 질문한다 | OpenSearch/Elasticsearch, Qdrant, RAG, Ollama | 키워드·vector·RAG를 필요한 범위에서만 켠다 |
| 8 | 파티와 운영자에게 소식을 보낸다 | WebSocket, webhook, Email, SMS | live hint와 durable event를 구분한다 |
| 9 | 퀘스트 문구를 보조한다 | OpenAI Responses API boundary, fake | 비용·권한 정책을 handler에 명시한다 |
| 10 | 서버를 관제하고 확장한다 | ELK, service token, Control Plane heartbeat, Compose HA, Kubernetes | 로그·health·instance 상태를 각각 확인한다 |
| 11 | 대장간 자체를 확장한다 | Plugin discovery, validator, CI, isolated Git generation | 확장은 Plugin 계약과 검증 gate를 통과한다 |

Level 0과 11은 **AutoForge 자체를 다루는 퀘스트**이고, Level 1~10은 AutoForge가
생성한 서버에 기능을 조합하는 퀘스트다. Plugin은 현재 서버 handler를 대신 작성하는
기능이 아니라 생성기·검증기를 확장하는 경계다. Git 자동화도 여러분의 작업 폴더를
직접 바꾸지 않고 격리 workspace에서 검증한 뒤에만 다음 단계로 간다. 정확한 계약은
[Plugin System](../architecture/plugin_system.md),
[Git Automation](../architecture/git_automation.md),
[Control Plane](../architecture/control_plane_persistence.md)을 따른다.

## Quest Rule. 새 도메인을 만들 때의 고정 순서

새 도메인은 항상 이 순서로 만든다.

```text
업무 문장 한 줄
  → 필요한 영속 데이터 결정
  → 필요한 공통 서비스만 선택
  → YAML 명세 작성
  → AutoForge generate
  → SCAFFOLDED handler 작성
  → 작은 테스트
  → Docker HTTP 확인
  → 실패·재시작 확인
```

예를 들어 “로그인한 사용자가 자기 표시 이름을 바꾼다”는 다음처럼 해석한다.

| 질문 | 답 | 선택 결과 |
| --- | --- | --- |
| 누가 변경하는가? | 로그인한 사용자 | `current_session` dependency |
| 무엇을 오래 저장하는가? | `user_id`, `display_name`, `updated_at` | PostgreSQL table/repository |
| 재시도하면 어떻게 되는가? | 같은 수정은 한 번의 결과 | `idempotency: true` |
| 요청 밖에서 할 일이 있는가? | 없다 | RabbitMQ를 선택하지 않음 |
| 파일·검색·AI가 필요한가? | 없다 | Storage/Search/RAG를 선택하지 않음 |

이 판단이 “서비스를 조합한다”는 말의 실제 뜻이다. Handler는 `SessionStore`나
Repository 같은 작은 계약만 받고, Redis host·PostgreSQL DSN·replica 수를 직접
알지 않는다.

## Level 1. 플레이어 카드 만들기: DB·SQL·Redis·로그

### 4.1 안전한 별도 명세 만들기

첫 가이드의 YAML을 복사한다. 생성된 서버 폴더가 아니라 **명세 폴더**를 복사하는
이유는, 재생성 가능한 입력과 생성 결과를 섞지 않기 위해서다.

```powershell
Copy-Item -Recurse `
  C:\workspace\login-server-spec `
  C:\workspace\profile-server-spec
```

`C:\workspace\profile-server-spec\autoforge.yaml` 전체를 다음으로 바꾼다.

```yaml
spec_version: "1"

project:
  name: Profile Server
  package_name: profile_server
  version: "0.1.0"
  description: Login and profile service workshop

tooling:
  docker:
    enabled: true
  local_environment:
    enabled: true
    application_enabled: true
    host_port_base: 49200

application:
  framework: fastapi
  modules:
    - identity
    - system
    - profile
  services:
    - name: session
      kind: redis_session
      namespace: profile_server_session
      ttl_seconds: 3600
  databases:
    - name: identity
      global_url_env: IDENTITY_DATABASE_URL
    - name: profile
      global_url_env: PROFILE_DATABASE_URL
```

`49200`은 이 실습의 HTTP 포트다. `49700`은 AutoForge Control Plane용 중앙 포트로
예약되어 있어 일반 서버 실습에 쓰지 않는다. 이미 다른 실습이 `49200` 블록을 쓴다면
100 단위 블록 전체를 바꾼다. 생성 뒤 4.4절에서 `.env`를 만든 후 포트 검사를 실행한다.
포트 규칙의 이유는 [로컬 포트 정책](../architecture/local_port_policy.md)에 있다.
Docker가 `ports are not available`이라고 하면 첫 가이드 8절의 Windows 예약 포트 확인법을
따르고, `.env`나 generated Compose를 직접 고치지 말고 명세의 `host_port_base`를 바꾼 뒤
다시 생성한다.

### 4.2 `profile.yaml` 작성

`C:\workspace\profile-server-spec\specifications\profile.yaml`을 새로 만든다.

```yaml
spec_version: "1"

module:
  name: profile
  display_name: Profile
  route_prefix: /api/profile

models:
  - name: UserProfile
    fields:
      - name: user_id
        type:
          kind: uuid
      - name: display_name
        type:
          kind: string
      - name: updated_at
        type:
          kind: datetime

endpoints:
  - name: get_my_profile
    method: GET
    path: /me
    response:
      fields:
        - name: user_id
          type:
            kind: uuid
        - name: display_name
          type:
            kind: string
        - name: updated_at
          type:
            kind: datetime
    handler: get_my_profile
    dependencies:
      - current_session
      - database_session_registry
  - name: update_my_profile
    method: PUT
    path: /me
    request:
      fields:
        - name: display_name
          type:
            kind: string
    response:
      fields:
        - name: user_id
          type:
            kind: uuid
        - name: display_name
          type:
            kind: string
        - name: updated_at
          type:
            kind: datetime
    handler: update_my_profile
    dependencies:
      - current_session
      - database_session_registry
    idempotency: true
    idempotency_ttl_seconds: 86400

database:
  provider: agnostic
  tables:
    - name: user_profiles
      columns:
        - name: user_id
          type:
            kind: uuid
          primary_key: true
        - name: display_name
          type:
            kind: string
        - name: updated_at
          type:
            kind: datetime
  repositories:
    - name: UserProfileRepository
      aggregate: UserProfile
      table: user_profiles
      operations:
        - find_by_id
        - save
  placements:
    - table: user_profiles
      store: profile
      mode: global
      unresolved_policy: error
```

`current_session`은 generated Router가 `Authorization: Bearer <token>`을 읽어
`SessionData`로 바꿔 handler에 넣게 한다. `idempotency: true`는 generated Router가
`Idempotency-Key` header를 검사하고, 같은 요청을 Redis replay store에서 다시
보내게 한다. Handler에 Redis client를 직접 추가할 필요가 없다.

### 4.3 생성하고 출력 경계 확인

```powershell
Set-Location C:\src\AutoForge
python -m autoforge.main generate `
  --project C:\workspace\profile-server-spec\autoforge.yaml `
  --specifications C:\workspace\profile-server-spec\specifications `
  --output C:\workspace\profile-server
```

성공 문구는 `Generated and validated`다. 생성 뒤 아래 파일들이 있는지 확인한다.

```text
src/profile_server/modules/profile/generated/models.py
src/profile_server/modules/profile/generated/router.py
src/profile_server/modules/profile/generated/sqlalchemy_repositories.py
src/profile_server/modules/profile/handlers.py
migrations/profile/env.py
migrations/profile/versions/0001_profile.py
database/global/0001_profile.sql
environment/postgres-init/00-databases.sql
```

`generated/` 파일, raw SQL, Alembic 환경(`migrations/profile/env.py`)은 명세에서
다시 만들 수 있는 AutoForge 소유 파일이다. 수정하지 않는다. 반면
`migrations/profile/versions/0001_profile.py`는 첫 생성 때만 만드는 **SCAFFOLDED
baseline**이다. 이것은 이미 배포한 DB의 이력이므로, 실행 중인 서버에서 다시 쓰거나
교체하지 않는다. 여러분이 구현할 파일은 `modules/profile/handlers.py`다.

이제 “YAML 한 장이 SQL을 만들었다”는 사실을 눈으로 확인한다.

```powershell
Set-Location C:\workspace\profile-server
Get-Content database\global\0001_profile.sql
Get-Content migrations\profile\versions\0001_profile.py
```

두 파일에 `user_profiles`를 만드는 구문이 보이면 Level 1의 DB·SQL 생성은 클리어다.
나중에 테이블을 바꿔야 하면 실행 중인 baseline을 고치는 대신, 명세의
`database.migrations`에 새 additive revision을 선언한다. 이 구분의 자세한 근거는
[생성 계약](../architecture/generation_contract.md), DB 생성물의 역할은
[Database Generation](../architecture/database_generation.md)을 참고한다.

### 4.4 환경을 만들고 기본 로그인 기능을 먼저 완성

```powershell
Set-Location C:\workspace\profile-server
Copy-Item environment\.env.example environment\.env

Set-Location C:\src\AutoForge
python -m autoforge.main validate-ports `
  --env-file C:\workspace\profile-server\environment\.env
```

`profile-server`도 login 기능을 포함하므로, [로그인 서버 가이드](login_server_from_zero.md)의
9~13절을 이번 경로와 `profile_server` package 이름에 맞춰 반복한다. 즉,
`system/handlers.py`, `identity/passwords.py`, `identity/handlers.py`를 먼저 구현하고
signup → login → session 검증이 통과해야 한다. 여기서 만든 access token이 다음
프로필 요청의 Bearer token이다. 첫 가이드의 Python 예시에 있는 모든
`login_server` import prefix는 `profile_server`로 바꾼다.

### 4.5 프로필 handler 구현

`C:\workspace\profile-server\src\profile_server\modules\profile\handlers.py`의 내용을
다음으로 바꾼다.

```python
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException

from profile_server.infrastructure.database.routing import ShardTarget
from profile_server.infrastructure.database.session import AsyncSessionRegistry
from profile_server.infrastructure.session_store.protocol import SessionData
from profile_server.modules.profile.generated.models import UserProfile
from profile_server.modules.profile.generated.schemas import (
    GetMyProfileResponse,
    UpdateMyProfileRequest,
    UpdateMyProfileResponse,
)
from profile_server.modules.profile.generated.sqlalchemy_repositories import (
    SQLAlchemyUserProfileRepository,
)

PROFILE_TARGET = ShardTarget(store="profile")


async def get_my_profile(
    current_session: SessionData,
    session_registry: AsyncSessionRegistry,
) -> GetMyProfileResponse:
    user_id = UUID(current_session.user_id)
    async with session_registry.session(PROFILE_TARGET) as session:
        profile = await SQLAlchemyUserProfileRepository(session).find_by_id(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return GetMyProfileResponse(**profile.model_dump())


async def update_my_profile(
    request: UpdateMyProfileRequest,
    current_session: SessionData,
    session_registry: AsyncSessionRegistry,
) -> UpdateMyProfileResponse:
    display_name = request.display_name.strip()
    if not display_name:
        raise HTTPException(status_code=422, detail="display_name must not be empty")
    user_id = UUID(current_session.user_id)
    updated_at = datetime.now(UTC)
    async with session_registry.session(PROFILE_TARGET) as session:
        repository = SQLAlchemyUserProfileRepository(session)
        profile = await repository.find_by_id(user_id)
        if profile is None:
            profile = UserProfile(
                user_id=user_id,
                display_name=display_name,
                updated_at=updated_at,
            )
        else:
            profile.display_name = display_name
            profile.updated_at = updated_at
        await repository.save(profile)
    return UpdateMyProfileResponse(**profile.model_dump())
```

`ShardTarget(store="profile")`은 프로필이라는 논리 store를 고르는 코드다. 지금은
global DB 한 개지만, 나중에 shard가 생겨도 handler가 DSN을 직접 알지 않게 한다.

### 4.6 Docker를 시작하고 HTTP로 검증

이미지와 database migration을 실행한다.

```powershell
Set-Location C:\workspace\profile-server
docker compose --env-file environment\.env -f environment\compose.integration.yml up -d --build --wait
docker compose --env-file environment\.env -f environment\compose.integration.yml ps
Invoke-RestMethod -UseBasicParsing http://127.0.0.1:49200/health
```

회원가입과 로그인은 첫 가이드 13절과 같지만 이번 주소는 `49200`이다.

```powershell
$signupBody = @{ email = "chimp@example.com"; password = "local-only-password" } | ConvertTo-Json
Invoke-RestMethod -UseBasicParsing -Method Post `
  -Uri http://127.0.0.1:49200/api/identity/signup `
  -ContentType "application/json" -Body $signupBody

$login = Invoke-RestMethod -UseBasicParsing -Method Post `
  -Uri http://127.0.0.1:49200/api/identity/login `
  -ContentType "application/json" -Body $signupBody

$headers = @{
  Authorization = "Bearer $($login.access_token)"
  "Idempotency-Key" = [guid]::NewGuid().ToString()
}
$profileBody = @{ display_name = "Chimp" } | ConvertTo-Json
```

프로필을 처음 만들고, 같은 요청을 같은 key로 한 번 더 보낸다.

```powershell
$first = Invoke-RestMethod -UseBasicParsing -Method Put `
  -Uri http://127.0.0.1:49200/api/profile/me `
  -Headers $headers -ContentType "application/json" -Body $profileBody

$replay = Invoke-RestMethod -UseBasicParsing -Method Put `
  -Uri http://127.0.0.1:49200/api/profile/me `
  -Headers $headers -ContentType "application/json" -Body $profileBody

$first
$replay
$first.updated_at -eq $replay.updated_at
```

마지막 줄이 `True`면 두 번째 요청은 별도 수정이 아니라 저장된 첫 응답을 replay한
것이다. 이어서 같은 Bearer token으로 조회한다.

```powershell
Invoke-RestMethod -UseBasicParsing -Method Get `
  -Uri http://127.0.0.1:49200/api/profile/me `
  -Headers @{ Authorization = "Bearer $($login.access_token)" }
```

이제 같은 `Idempotency-Key`에 **다른** 본문을 보내면 `409`가 나야 한다. 이는 실수로
한 key를 다른 의도로 재사용하는 상황을 막는다.

```powershell
$differentBody = @{ display_name = "Different name" } | ConvertTo-Json
try {
  Invoke-RestMethod -UseBasicParsing -Method Put `
    -Uri http://127.0.0.1:49200/api/profile/me `
    -Headers $headers -ContentType "application/json" -Body $differentBody
  throw "409 응답이 필요합니다."
} catch {
  if ($_.Exception.Response.StatusCode.value__ -ne 409) { throw }
  "Expected 409: one Idempotency-Key cannot represent two bodies."
}
```

이제 같은 행동이 세 군데에 남는다. HTTP 응답은 플레이어가 본 결과, PostgreSQL은
영속된 결과, Compose 로그는 서버가 처리한 흔적이다. 문제를 만났을 때는 Docker 전체를
재설치하지 말고 다음 세 로그부터 확인한다.

```powershell
docker compose --env-file environment\.env -f environment\compose.integration.yml logs application --tail 100
docker compose --env-file environment\.env -f environment\compose.integration.yml logs postgres --tail 100
docker compose --env-file environment\.env -f environment\compose.integration.yml logs redis --tail 100
```

`logs` 폴더에 `.log` 파일을 연결한 실행 환경이라면 Filebeat/ELK도 같은 파일을 읽는다.
애플리케이션은 Elasticsearch에 직접 쓰지 않는다.

## Level 2 이후. 퀘스트를 하나씩 확장한다

프로필 실습이 통과한 뒤에만 아래 중 실제 도메인이 요구하는 한 가지를 고른다. 각
YAML 조각은 기존 `autoforge.yaml`의 같은 위치에 **추가 또는 병합**한다. 여러 조각을
한 번에 복사하지 않는다.

### Level 2. 보상 상자 배달: RabbitMQ, Outbox, Durable Job, Airflow

**미션:** 플레이어가 퀘스트를 완료하면 보상을 지급하고, 내일 아침에는 새 일일 퀘스트를
연다. 보상 전송이 잠시 실패해도 플레이어 카드 저장은 잃지 않는다.

**AutoForge:** PostgreSQL transaction 안의 Outbox, RabbitMQ relay/worker, 선택한
Durable Job과 Airflow 호출 경로를 생성한다.

**내 코드:** 어떤 event를 기록할지, consumer가 실제로 무엇을 할지, 보상이 이미 지급된
경우 어떻게 처리할지를 작성한다.

**클리어:** `rabbitmq`, `outbox-relay`, `message-worker`, `durable-job-worker`가
healthy이고, 아래의 deterministic job handler 테스트와 내부 HTTP job 요청이 모두
통과한다.

“프로필 변경 후 환영 메일을 보내기”처럼 DB commit 뒤 별도 작업이 필요할 때 쓴다.
같은 DB transaction에 profile 변경과 Outbox 기록을 남기고, relay/worker가 RabbitMQ를
통해 후속 처리를 한다. HTTP handler가 RabbitMQ publish 성공을 직접 기다리지 않는다.

```yaml
application:
  services:
    - name: events
      kind: rabbitmq
      outbox_stores:
        - profile
      exchange: profile.events
      queue: profile.events.worker
      routing_key: profile.#
  durable_jobs:
    - name: daily_profile_check
      store: profile
      event_type: profile.check.requested
      routing_key: profile.check.requested
      schedule: "0 9 * * *"
```

이 첫 local 실습은 RabbitMQ 기본 `classic` queue를 쓴다. `quorum` queue는 나중에
RabbitMQ cluster를 선택하는 HA 실습에서만 사용한다. 여기서 `queue_type`을 쓰지 않는
것은 설정을 빼먹은 것이 아니라, 한 대 PC에서 먼저 메시지 흐름을 확인하기 위한 기본값
선택이다.

### Level 2.1 사용자 소유 job handler를 하나 구현한다

`src/profile_server/application/durable_job_handler.py`는 SCAFFOLDED 파일이다. 아래처럼
작은 결정론적 결과부터 돌려준다. 실제 보상 지급 규칙은 이 함수에 작성하고, RabbitMQ
connection·Outbox relay·상태 전이는 generated infrastructure에 맡긴다.

```python
from profile_server.infrastructure.database.session import AsyncSessionRegistry
from profile_server.infrastructure.durable_jobs.worker import DurableJobExecution


class ApplicationDurableJobHandler:
    async def handle(
        self, execution: DurableJobExecution
    ) -> dict[str, object] | None:
        return {
            "job_type": execution.job_type,
            "run_key": execution.run_key,
        }


def validate_durable_job_payload(
    job_type: str, payload: dict[str, object]
) -> None:
    del job_type, payload


def create_durable_job_handler(
    session_registry: AsyncSessionRegistry,
) -> ApplicationDurableJobHandler:
    del session_registry
    return ApplicationDurableJobHandler()
```

먼저 이 코드만 확인한다.

`tests/test_durable_job_handler.py`:

```python
import pytest

from profile_server.application.durable_job_handler import ApplicationDurableJobHandler
from profile_server.infrastructure.durable_jobs.worker import DurableJobExecution


@pytest.mark.anyio
async def test_durable_job_handler_returns_a_deterministic_result() -> None:
    result = await ApplicationDurableJobHandler().handle(
        DurableJobExecution(
            job_id="job-1",
            job_type="daily_profile_check",
            run_key="guide-check-1",
            payload={},
        )
    )

    assert result == {"job_type": "daily_profile_check", "run_key": "guide-check-1"}
```

```powershell
Set-Location C:\workspace\profile-server
python -m pytest tests\test_durable_job_handler.py -q
```

### Level 2.2 내부 HTTP 요청으로 RabbitMQ worker까지 확인한다

공통 네 단계를 끝내면 `airflow-db-bootstrap`은 이미 존재하는 PostgreSQL volume에도
Airflow용 DB를 한 번만 만들고 종료한다. 따라서 Level 1의 profile 데이터를 지우기 위해
`down --volumes`를 실행할 필요가 없다.

SCAFFOLDED handler를 이미지에 넣고, local `.env`의 내부 service token으로 job을 요청한다.

```powershell
Set-Location C:\workspace\profile-server
docker compose --env-file environment\.env `
  -f environment\compose.integration.yml up -d --build application durable-job-worker

$jobToken = (Get-Content environment\.env |
  Where-Object { $_ -match '^DURABLE_JOB_API_TOKEN=' } |
  Select-Object -First 1) -replace '^DURABLE_JOB_API_TOKEN=', ''
$jobHeaders = @{ Authorization = "Bearer $jobToken" }
$jobBody = @{ run_key = "guide-check-$([guid]::NewGuid())"; payload = @{} } |
  ConvertTo-Json

$job = Invoke-RestMethod -UseBasicParsing -Method Post `
  -Uri http://127.0.0.1:49200/internal/jobs/daily_profile_check `
  -Headers $jobHeaders -ContentType "application/json" -Body $jobBody

$deadline = (Get-Date).AddSeconds(30)
do {
  $jobState = Invoke-RestMethod -UseBasicParsing -Method Get `
    -Uri "http://127.0.0.1:49200/internal/jobs/daily_profile_check/$($job.job_id)" `
    -Headers $jobHeaders
  if ($jobState.status -in @("succeeded", "failed")) { break }
  Start-Sleep -Milliseconds 500
} while ((Get-Date) -lt $deadline)

if ($jobState.status -ne "succeeded") {
  throw "Job did not succeed: $($jobState | ConvertTo-Json -Compress)"
}

$jobState
```

`status: "succeeded"`와 `result.run_key`가 보이면, HTTP 요청은 DB에 job을 기록하고,
Outbox relay는 RabbitMQ event를 전달했으며, worker가 SCAFFOLDED handler를 실행한 것이다.
`/internal/jobs/*`는 일반 로그인 토큰이 아니라 내부 service token 전용 endpoint다.

### Level 2 이상에서 매번 하는 네 단계

아래 Level의 YAML 조각은 모두 `C:\workspace\profile-server-spec\autoforge.yaml`의 같은
최상위 항목에 **추가하거나 병합**한다. 예를 들어 `tooling:` 조각은 기존 `tooling:` 아래에
합친다. 같은 이름의 최상위 항목을 파일 끝에 두 번 만들지 않는다.

YAML 조각 하나를 합칠 때마다 다음 네 단계를 먼저 끝낸다. 다음 Level의 조각을 합치기
전에 이 Level의 `generate`와 healthcheck가 성공해야 한다.

```powershell
Set-Location C:\src\AutoForge
python -m autoforge.main generate `
  --project C:\workspace\profile-server-spec\autoforge.yaml `
  --specifications C:\workspace\profile-server-spec\specifications `
  --output C:\workspace\profile-server

if (-not (Test-Path C:\workspace\profile-server\environment\.env)) {
  Copy-Item C:\workspace\profile-server\environment\.env.example `
    C:\workspace\profile-server\environment\.env
}

python -m autoforge.main validate-ports `
  --env-file C:\workspace\profile-server\environment\.env

Set-Location C:\workspace\profile-server
docker compose --env-file environment\.env `
  -f environment\compose.integration.yml up -d --build --wait
docker compose --env-file environment\.env `
  -f environment\compose.integration.yml ps
```

기존 `.env`를 이미 만들었다면 `.env.example`을 덮어쓰지 않는다. 새 Level이 서비스나
환경값을 추가했을 때는 새 `.env.example`에서 **새로 생긴 줄을 모두** 기존 `.env`에
복사한다. 이 Level에서는 `RABBITMQ_USER`, `RABBITMQ_PASSWORD`,
`RABBITMQ_AMQP_PORT`, `RABBITMQ_MANAGEMENT_PORT`, `RABBITMQ_URL`, `AIRFLOW_PORT`,
`DURABLE_JOB_API_URL`, `DURABLE_JOB_API_TOKEN`이 추가된다.

별도 overlay를 만드는 Level은 위 네 단계 뒤에 그 Level에 적힌 별도 Compose 명령을
추가로 실행한다. `.env`, generated Compose, `generated/` 파일을 직접 고쳐 문제를
해결하지 않는다. 명세를 고친 뒤 다시 생성한다.

`schedule`이 있는 Durable Job은 local profile에서 Airflow가 API를 호출하는 경로를
생성한다. 이 서비스들은 단순 프로필 수정에 넣지 않는다. 먼저 “DB 변경은 성공했는데
메일 서버가 죽으면 어떻게 되는가?”라는 문제에 실제로 부딪혔을 때 선택한다. 정본은
[Event/Pipeline](../architecture/event_driven_architecture.md)과
[Database Outbox](../architecture/database_generation.md)다.

확인 순서는 `generate` → `docker compose ... ps`에서 `rabbitmq`, `outbox-relay`,
`message-worker`, `durable-job-worker` 확인 → 사용자 소유 job handler의 작은 test →
내부 HTTP job 요청 순서다.

### Level 3. 인기 퀘스트 순위표: Cache와 Distributed Lock

**미션:** 같은 순위표를 자주 읽어도 DB를 매번 읽지 않고, 여러 replica가 있어도 일일
보상 계산은 한 번만 한다.

**AutoForge:** Redis 또는 Memcached 기반 cache protocol/fake와 Redis 기반 lock protocol을
생성한다.

**내 코드:** cache key, TTL, invalidation 시점과 lock으로 감쌀 작은 critical section을
결정한다.

**클리어:** fake에서 cache miss/hit과 lock 경쟁을 확인하고, 선택한 Compose 서비스가
healthy임을 확인한다.

읽기 결과를 잠시 저장할 때는 Key-Value Store, 여러 replica 중 한 곳만 같은 작업을
할 때는 Distributed Lock을 선택한다. 세션 저장소에 임의 cache/lock 기능을 억지로
넣지 않는다.

```yaml
tooling:
  key_value_store:
    enabled: true
    backend: redis
    mode: standalone
    key_prefix: profile_cache
    ttl_seconds: 300
  distributed_lock:
    enabled: true
    mode: standalone
    key_prefix: profile_lock
    ttl_seconds: 30
```

`key_value_store.backend`는 `redis` 또는 `memcached`다. Redis는 standalone/Sentinel/
Cluster를, Memcached는 standalone만 지원한다. `distributed_lock`은 lock 보유 시간을
명시적으로 짧게 둔다. “빠르게 보이게 할 cache”나 “중복 실행이 실제로 가능한 작업”이
아니면 둘 다 추가하지 않는다.

확인은 generated fake로 handler 단위 테스트를 먼저 쓰고, 다음에 Compose `redis` 또는
`memcached`가 healthy인지 확인한다. topology를 바꿔도 도메인 handler가 Redis 주소를
알아서는 안 된다.

### Level 4. 뱃지 보관함: S3 호환 Object Storage와 MinIO

**미션:** 플레이어가 얻은 뱃지 이미지를 안전하게 보관하고 카드에는 그 위치만 남긴다.

**AutoForge:** S3 호환 Object Storage protocol/fake와 선택 가능한 local MinIO overlay를
생성한다.

**내 코드:** object key 규칙, 업로드 파일 형식·크기 검사, 읽기 권한과 삭제 시점을
결정한다.

**클리어:** MinIO Compose profile이 healthy이고, DB가 이미지 바이트가 아닌 object key만
보관함을 확인한다.

프로필 사진처럼 큰 바이너리는 DB 열이 아니라 object storage에 둔다. DB에는 object
key·소유자·메타데이터만 저장한다.

```yaml
tooling:
  storage:
    enabled: true
    runtime_enabled: true
    host_port_base: 49500
```

생성 후 local MinIO를 별도로 시작한다.

```powershell
Set-Location C:\workspace\profile-server
Copy-Item deploy\storage\.env.example deploy\storage\.env
docker compose --env-file deploy\storage\.env `
  -f deploy\storage\compose.storage.yaml --profile storage up -d
docker compose --env-file deploy\storage\.env `
  -f deploy\storage\compose.storage.yaml ps
```

MinIO는 로컬 S3 호환 검증용이다. 운영에서 AWS S3를 선택해도 handler는 generated
ObjectStorage protocol만 사용하고 URL/credential은 runtime 환경으로 받는다. 버킷
권한·파일 형식 검사·보존 기간은 도메인 정책이므로 여러분이 정한다.

### Level 5. NPC에게 외부 정보를 묻기: External Provider

**미션:** 퀘스트 NPC가 외부 날씨·환율·결제 정보를 가져오되, 외부 사이트가 느려도 내
서버가 멈추지 않는다.

**AutoForge:** async transport 경계와 정상·timeout·4xx·5xx를 재현하는 deterministic
fake를 생성한다.

**내 코드:** 외부 응답을 내 도메인 값으로 바꾸는 규칙, 사용자에게 보일 오류, 쓰기 요청의
idempotency를 결정한다.

**클리어:** 실제 API key 없이 fake 테스트를 통과한 뒤에만 `.env`/Secret으로 provider를
연결한다.

결제·증권·환율 같은 외부 API는 URL을 handler에 하드코딩하지 않는다.

```yaml
tooling:
  external_provider:
    enabled: true
    url_environment: PAYMENT_PROVIDER_URL
    health_path: /health
    timeout_seconds: 5
    max_retries: 2
```

생성된 fake로 정상·timeout·4xx·5xx를 먼저 테스트한다. 실제 provider URL·API key를
`.env`/Secret에 넣은 뒤에만 health 확인을 한다. 읽기 요청과 달리 결제·주문 같은 쓰기
요청은 자동 재시도에 기대지 말고, 도메인 idempotency 정책을 명시한다.

### Level 6. 퀘스트 도감: Search, Vector Store, RAG

**미션:** 제목으로 퀘스트를 찾고, 비슷한 모험 기록을 추천하며, 충분한 근거가 있을 때만
도감 질문에 답한다.

**AutoForge:** OpenSearch/Elasticsearch transport, Qdrant transport/fake와 local
Search+Qdrant+Ollama RAG overlay를 각각 생성한다.

**내 코드:** index/collection에 넣을 문서, 권한 필터, embedding·hybrid ranking·답변
근거 정책을 결정한다.

**클리어:** keyword 검색·vector 검색·RAG를 각각 필요한 경우에만 켜고, 모델 다운로드 전
디스크 공간을 확인한다.

키워드 검색만 필요하면 Search, embedding 유사도만 필요하면 Vector Store를 고른다.
둘을 실제로 함께 쓰며 local 인프라가 필요할 때만 RAG overlay를 켠다.

```yaml
tooling:
  search:
    enabled: true
    backend: opensearch
    url_environment: SEARCH_URL
    default_index: profile_documents
  vector_store:
    enabled: true
    url_environment: VECTOR_DB_URL
    default_collection: profile_vectors
  rag:
    enabled: true
    search_backend: opensearch
    host_port_base: 49400
```

RAG overlay 시작은 별도 Compose 파일이다. Ollama는 큰 모델과 디스크 공간을 요구하므로
처음에는 `rag` profile만 실행한다.

```powershell
Set-Location C:\workspace\profile-server
Copy-Item deploy\rag\.env.example deploy\rag\.env
docker compose --env-file deploy\rag\.env `
  -f deploy\rag\compose.rag.yaml --profile rag up -d
docker compose --env-file deploy\rag\.env `
  -f deploy\rag\compose.rag.yaml ps
```

Search/VectorStore는 transport 경계만 생성한다. 어떤 필드를 index할지, embedding
모델·차원·hybrid ranking·권한 필터를 어떻게 정할지는 도메인 책임이다. 검색 화면이나
평가 데이터가 없는 상태에서 RAG를 먼저 켜지 않는다.

### Level 7. 파티 알림: Realtime·Webhook·Email·SMS

**미션:** 새 보상은 접속 중인 파티원에게 바로 보이고, 중요한 사건은 운영자나 사용자에게
적절한 전달 수단으로 남긴다.

**AutoForge:** WebSocket hub, 선택적 Redis Pub/Sub backplane, webhook/SMTP/SOLAPI
transport와 fake를 생성한다.

**내 코드:** 누가 어떤 채널을 구독하는지, durable event와 휘발성 live hint를 어떻게
구분하는지, 동의·재전송·비용 정책을 결정한다.

**클리어:** HTTP 도메인과 재시작이 먼저 안정적이고, 실제 수신 주소 없이 fake 전달
테스트를 통과한다.

| 필요 | 명세 | handler가 책임지는 것 | 먼저 할 확인 |
| --- | --- | --- | --- |
| WebSocket 알림 | `tooling.realtime.enabled: true` | 어떤 사용자/채널에 어떤 힌트를 보낼지 | HTTP 도메인·재시작이 안정적인가 |
| 여러 API replica 실시간 전달 | `tooling.realtime.backplane: redis_pubsub` | durable record와 live hint의 구분 | `redis_session`이 정확히 하나인가 |
| 운영 webhook | `tooling.notification.enabled: true` | 어떤 사건을 보낼지 | 수신 webhook URL이 준비됐는가 |
| 메일 | `tooling.email.enabled: true` | template·수신 동의·재전송 정책 | SMTP 설정과 fake 테스트 |
| 문자 | `tooling.sms.enabled: true` | 전화번호 검증·비용·인증 정책 | SOLAPI key/secret/sender 준비 |

Email·SMS·Webhook은 전달 수단일 뿐, “어떤 이벤트를 누구에게 몇 번 보내는가”는
도메인 정책이다. 신뢰성 있는 전달이 필요하면 먼저 Level 2의 Outbox를 결합한다.

필요한 전달 수단 하나의 설정만 추가한다. 아래는 정확한 최소 시작점이며, 모두를
한꺼번에 켜라는 예시는 아니다.

```yaml
tooling:
  realtime:
    enabled: true
    backplane: redis_pubsub
    channel: profile.notifications.v1
  notification:
    enabled: true
    webhook_url_environment: NOTIFICATION_WEBHOOK_URL
  email:
    enabled: true
    host_environment: SMTP_HOST
    port_environment: SMTP_PORT
    sender_environment: SMTP_SENDER
  sms:
    enabled: true
    api_key_environment: SOLAPI_API_KEY
    api_secret_environment: SOLAPI_API_SECRET
    sender_environment: SOLAPI_SENDER
```

Realtime backplane은 `redis_session` service가 정확히 하나일 때만 선택할 수 있다.
Webhook/SMTP/SOLAPI 주소와 비밀값은 `.env` 또는 배포 Secret에만 넣는다. 외부 전달은
수신 측이 준비되기 전에는 deterministic fake 테스트로 확인한다.

### Level 8. 퀘스트 작가: LLM

**미션:** AI가 퀘스트 요약 문구를 제안하지만, 플레이어 데이터와 비용은 도메인 정책 안에서
통제한다.

**AutoForge:** OpenAI Responses API 경계와 deterministic fake를 생성한다.

**내 코드:** prompt, 개인정보 마스킹, 사용 권한, token 예산, 결과 저장 여부를 정한다.

**클리어:** 실제 API key 없이 fake 테스트가 통과하고, key는 `.env` 또는 Secret에만
존재한다.

```yaml
tooling:
  llm:
    enabled: true
    model: your-selected-model
    api_key_environment: OPENAI_API_KEY
    timeout_seconds: 30
```

생성된 LLM service는 OpenAI Responses API 호출 경계와 deterministic fake를 제공한다.
prompt, 개인정보 마스킹, 사용 권한, token 비용 한도, 결과를 DB에 저장할지 여부는
생성기가 대신 결정하지 않는다. 먼저 fake로 handler 테스트를 통과시키고, 실제 key는
Git에 올리지 않는 환경값으로만 주입한다.

### Level 9. 관제탑: ELK

**미션:** 플레이어가 “보상이 안 왔어요”라고 말하면 한 request의 로그를 찾아 원인을
추적한다.

**AutoForge:** Filebeat, Elasticsearch, Kibana를 포함한 central ELK overlay 또는
외부 중앙 수집기로 보내는 collector overlay를 생성한다.

**내 코드:** 로그에 넣을 업무 식별자와 민감정보를 절대 남기지 않는 정책을 결정한다.

**클리어:** 애플리케이션이 `logs/*.log`를 남기고 Filebeat가 그 파일을 수집하며,
Kibana에서 request 단위로 검색할 수 있다.

도메인 기능이 HTTP와 Docker에서 정상 동작한 뒤, JSON 로그를 찾아볼 필요가 생기면
ELK overlay를 추가한다.

```yaml
tooling:
  elk:
    enabled: true
    mode: central
    host_port_base: 49600
```

생성 뒤 시작 명령은 다음과 같다.

```powershell
Set-Location C:\workspace\profile-server
docker compose --env-file environment\.env `
  -f environment\compose.integration.yml `
  -f deploy\observability\compose.elk.yaml up -d
```

애플리케이션은 Elasticsearch를 직접 호출하지 않고 `logs/*.log`를 남긴다. Filebeat가
수집하고 Elasticsearch/Kibana가 저장·조회한다. 여러 인스턴스가 있다면 중앙 ELK는
한 번만, 각 인스턴스는 `collector` mode를 선택한다. 정본은
[관측성 자동생성](../architecture/observability_generation.md)이다.

## Level 10. 난이도 조절: DB와 실행 환경을 도메인 코드에서 분리한다

**미션:** 같은 Quest Board를 노트북 한 대에서는 가볍게, 검증 환경에서는 여러 container와
replica로, 운영에서는 Kubernetes로 실행한다.

**AutoForge:** local environment, Docker Compose healthcheck, single-host HA,
Kubernetes base-server profile, Control Plane heartbeat와 service-token guard를
각각 선택적으로 생성한다.

**내 코드:** handler는 Repository와 service protocol만 사용한다. replica 수, DB provider,
DSN, Secret 이름, 내부 호출 권한은 handler 밖의 명세·환경값에서 결정한다.

**클리어:** single mode의 HTTP/restart 검증을 끝낸 뒤 HA profile을 올리고, 운영자가
필요할 때만 heartbeat·service token·Kubernetes를 추가한다.

프로필 handler의 `ShardTarget(store="profile")`과 Repository 사용법은 다음 설정이
바뀌어도 바뀌지 않아야 한다.

```yaml
tooling:
  local_environment:
    enabled: true
    application_enabled: true
    database_provider: postgresql  # 또는 mysql
    postgres_mode: standalone      # 검증 뒤 ha
    mysql_mode: standalone         # MySQL 선택 시
  single_host:
    enabled: false                 # 단일 모드가 통과한 뒤 true
    application_replicas: 3
```

개발 첫 단계는 PostgreSQL standalone 한 개와 FastAPI 한 개다. 이후 HA profile에서
database·Redis·RabbitMQ·application replica를 늘리더라도 handler는 interface만
사용한다. 한 대 PC의 HA 검증은 container/service 복구 검증이며 host 장애 보장은
아니다. 경계와 검증 범위는 [환경 검증 계약](../architecture/environment_validation_contract.md)을
따른다.

서버 운영자가 필요한 순간에는 다음처럼 **선택적으로** 운영 경계를 더한다. 실제 image,
Secret, namespace가 준비되기 전에는 이 조각을 복사하지 않는다.

```yaml
application:
  control_plane_heartbeat:
    enabled: true
    interval_seconds: 30
  service_tokens:
    - name: quest_worker
      token_env: QUEST_WORKER_API_TOKEN

tooling:
  kubernetes:
    enabled: true
    namespace: quest-board
    image: registry.example.com/quest-board:0.1.0
    secret_name: quest-board-runtime
    application_replicas: 3
    proxy_replicas: 2
```

Heartbeat은 “이 instance가 살아 있다고 보고하는” push 관측 정보다. `/health`와
`/readiness` probe를 대체하지 않는다. `service_token`은 internal endpoint가 해당
scope를 명시할 때만 적용한다. Secret 값은 YAML에 넣지 않고 deployment 환경에서
주입한다.

## Level 11. 대장간 확장: Plugin, CI, Git 자동화

**미션:** Quest Board의 업무 코드는 그대로 두고, 여러 프로젝트에 반복되는 생성·검증
규칙만 AutoForge 자체에 추가한다.

**Plugin:** plugin manifest 발견은 Python 코드를 실행하지 않고 metadata·의존성·권한을
검사한다. 실제 loading은 신뢰한 plugin에 한해 명시적으로 수행한다. 이미 있는 generator나
validator로 해결되면 Plugin을 만들지 않는다.

**CI와 Git 자동화:** Generator는 Git을 모르며, Git 자동화는 사용자 working tree가 아닌
격리 workspace에서 checkout → generate/validate → 허용된 변경만 commit/push/PR 순으로
처리한다. 따라서 “빠르게 고치기”를 위해 generated 파일을 직접 수정하는 도구가 아니다.

**클리어:** 새 Plugin은 metadata와 작은 generator/validator 테스트를 먼저 통과하고,
Git 작업은 validation gate가 성공한 경우에만 다음 단계로 진행한다. 구체 계약은
[Plugin System](../architecture/plugin_system.md)과
[Git Automation](../architecture/git_automation.md)이 소유한다.

## Every Level. 공통 클리어 테스트 순서

서비스가 늘어나도 테스트 순서는 바꾸지 않는다.

```text
1. YAML generate validation
2. 새 handler의 fake 또는 순수 함수 테스트
3. 선택한 service의 healthcheck
4. HTTP happy path
5. 인증 실패·입력 오류·중복 요청
6. 필요한 경우 한 컨테이너 재시작 뒤 동일 확인
7. 그 뒤에만 HA/외부 provider/실제 credential 검증
```

실패하면 전체 서비스를 재설치하거나 Docker 전체를 정리하지 않는다. 먼저 생성
프로젝트의 `environment/service-composition.json`, `docker compose ... ps`, 해당
서비스 로그를 차례로 확인한다. 이 manifest는 선택된 서비스의 환경 변수, healthcheck,
의존 관계, restart 정책을 generated 정보로 보여 준다.

## 다음 퀘스트 하나를 고르기

프로필 도메인까지 성공했다면 다음 중 **하나만** 선택한다.

1. 프로필 사진: Object Storage + image type/size 검증.
2. 비밀번호 재설정: Email + token 원장 + Outbox.
3. 운영 알림: Notification webhook + Outbox.
4. 공지 검색: Search + 사용자 소유 document projection.
5. 예약 데이터 수집: External Provider + Durable Job + Airflow.

어떤 것을 선택하든 명세를 먼저 바꾸고 생성한다. generated 파일을 직접 수정해
기능을 붙이는 방식은 재생성 때 사라지므로 사용하지 않는다.

## 이 퀘스트가 참조하는 정본 문서

- [전체 시스템 구조](../architecture/system_design.md)
- [명세 설계](../architecture/specification_design.md)
- [생성·소유권 계약](../architecture/generation_contract.md)
- [DB·Global/Shard·Outbox](../architecture/database_generation.md)
- [Redis 세션](../architecture/redis_services.md)
- [EventBus·Pipeline](../architecture/event_driven_architecture.md)
- [Docker Build](../architecture/docker_build_contract.md)
- [환경·저장소](../architecture/configuration_and_storage_policy.md)
- [로그·ELK](../architecture/observability_generation.md)
- [로컬 포트](../architecture/local_port_policy.md)
- [환경 검증 한계](../architecture/environment_validation_contract.md)

이 실습의 목적은 모든 서비스를 켜 보는 것이 아니다. 하나의 실제 도메인에 필요한
서비스를 고르고, 명세·생성·handler·테스트의 연결을 스스로 확인하는 것이다.
