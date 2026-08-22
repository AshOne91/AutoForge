# 처음부터 만드는 AutoForge 로그인 서버

> 문서 역할: GUIDE
>
> 이 문서는 Windows 컴퓨터에 개발 도구가 전혀 없다는 가정에서 시작한다.
> 목표는 AutoForge로 **로그인 서버의 뼈대**를 생성하고, 직접 작성한
> `회원가입 → 로그인 → Redis 세션 검증 → ping/pong`까지 로컬 Docker에서
> 확인하는 것이다. 이 문서는 현재 구조의 정본이 아니다. 생성 계약은
> [명세 설계](../architecture/specification_design.md),
> [생성 계약](../architecture/generation_contract.md),
> [DB 계약](../architecture/database_generation.md)를 따른다.

## 시작 전에: 지금 무엇을 만드는가

`AutoForge`는 로그인 서버 자체가 아니라, **서버의 반복되는 뼈대를 만드는 Python 생성기**다.
이 문서에서 만드는 `login-server`는 AutoForge를 검증하면서 배우기 위한 첫 번째 결과물이다.

```text
사람이 요구사항을 YAML로 적음
        ↓
AutoForge가 DB·SQL·FastAPI Router·Docker 환경을 생성함
        ↓
사람이 handlers.py에 "회원가입하면 무엇을 할지" 같은 업무 규칙을 작성함
        ↓
Docker가 PostgreSQL·Redis·FastAPI를 함께 실행함
```

처음 보는 사람에게 가장 중요한 구분은 세 가지다.

| 질문 | 답 |
| --- | --- |
| AutoForge에 작성하는 것은? | 서버의 구조와 계약을 적은 YAML 명세 |
| 생성된 서버에 작성하는 것은? | `handlers.py`의 실제 업무 규칙과 테스트 |
| Docker가 하는 일은? | 내 컴퓨터에서 서버와 DB·Redis를 같은 방식으로 함께 실행 |

따라서 이 문서의 명령은 순서가 있다. `git clone`은 생성기를 받는 일, `conda create`는
이 프로젝트 전용 Python 상자를 만드는 일, `generate`는 서버 뼈대를 만드는 일,
`docker compose up`은 만들어진 서버를 실제로 켜는 일이다. 각 명령 뒤에는 다음 절의
확인 결과가 나와야 하며, 결과가 다르면 다음 단계로 넘어가지 않는다.

## 0. 이 문서로 만드는 것과 만들지 않는 것

완료하면 다음 그림처럼 동작한다.

```text
브라우저 / PowerShell
        |
        v
FastAPI 로그인 서버 (49300)
        |                 \
        v                  v
PostgreSQL (49310)      Redis (Compose 내부)
  계정 원장              로그인 세션
```

- `POST /api/identity/signup`: 이메일과 비밀번호로 계정을 만든다.
- `POST /api/identity/login`: 비밀번호를 확인하고 Redis 세션 토큰을 만든다.
- `POST /api/identity/session/validate`: 세션 토큰이 아직 유효한지 확인한다.
- `GET /api/system/ping`: `{"message":"pong"}`을 돌려준다.

이 첫 서버에는 일부러 넣지 않는다.

- 주문, 결제, 투자 전략, 외부 API
- RabbitMQ, Worker, Airflow, RAG, Elasticsearch
- WebSocket, 이메일 인증, 비밀번호 재설정, OAuth
- 다중 물리 서버와 Kubernetes

처음에는 필요한 것만 만든다. PostgreSQL과 Redis는 이후에도 그대로
재사용하는 공통 기반이다. RabbitMQ 같은 비동기 서비스는 실제로 백그라운드
작업이 생겼을 때 추가한다.

## 1. 가장 먼저 알아둘 단어

| 단어 | 쉬운 설명 |
| --- | --- |
| 서버 | 요청을 받고 응답을 주는 실행 중인 프로그램 |
| FastAPI | Python으로 HTTP API 서버를 만드는 도구 |
| Docker | 프로그램과 필요한 환경을 컨테이너로 묶어 실행하는 도구 |
| Compose | 여러 컨테이너를 함께 시작하는 Docker 설정 |
| PostgreSQL | 계정처럼 오래 보관해야 하는 데이터를 저장하는 DB |
| Redis | 로그인 세션처럼 빠르게 읽고 지우는 데이터를 저장하는 서비스 |
| 명세(YAML) | 서버에 무엇이 필요한지 AutoForge에 설명하는 설계 입력 |
| 생성 코드 | 명세로부터 반복해서 만들어지는 코드. 직접 고치지 않는다. |
| SCAFFOLDED 코드 | 한 번 만들어진 뒤 사람이 구현하는 파일. 이 서버의 handler가 여기에 해당한다. |
| 도메인/모듈 | `identity`, `profile`처럼 한 가지 업무를 묶은 코드 단위. 이 실습의 `identity`는 회원가입·로그인 업무다. |
| Router | URL과 HTTP 메서드를 handler에 연결하는 입구 코드. AutoForge가 생성한다. |
| Handler | Router가 넘긴 요청을 받아 실제 업무 규칙을 실행하는 함수. 사람이 작성한다. |
| Endpoint | `POST /api/identity/login`처럼 외부 프로그램이 호출하는 한 개의 URL 규칙. |
| `.env` 환경 파일 | 비밀번호, 포트처럼 컴퓨터마다 다른 값을 코드 밖에 두는 파일. Git에 올리지 않는다. |
| Migration | DB table을 처음 만들거나 바꾸는 순서를 기록한 파일. raw SQL과 Alembic 환경은 AutoForge가 재생성하지만, 최초 Alembic baseline은 한 번 만든 뒤 이력으로 보존한다. Docker 시작 때 적용한다. |
| Health check | 서버가 살아 있을 뿐 아니라 요청을 받을 준비가 됐는지 확인하는 `/health` 요청. |

가장 중요한 경계는 다음 한 줄이다.

```text
명세 → AutoForge 생성 → GENERATED 코드 → SCAFFOLDED handler → 실제 로그인 규칙
```

AutoForge는 DB 모델, SQL, FastAPI Router, Docker Compose, Redis 연결 코드를
만든다. 여러분은 “어떤 비밀번호가 맞는가”, “로그인 실패를 어떻게 처리하는가”
같은 도메인 규칙을 handler에 작성한다.

## 2. 설치 전 준비

### 2.1 사용할 폴더

아래 경로를 그대로 사용하면 명령을 따라 하기 쉽다. 공백이나 한글이 없는
경로를 권장한다.

```text
C:\src\AutoForge                 # 생성기 소스
C:\workspace\login-server-spec   # 사람이 관리하는 YAML 명세
C:\workspace\login-server        # AutoForge가 생성하는 서버
```

`login-server-spec`와 `login-server`를 나누는 이유는 간단하다. 앞은 설계 입력,
뒤는 생성 결과와 여러분의 handler다. 명세를 바꿔 다시 생성해도 어느 쪽을
고쳐야 하는지 혼동하지 않는다.

### 2.2 설치할 프로그램

다음 순서대로 설치한다.

1. [Git for Windows](https://git-scm.com/download/win)
2. [Miniconda for Windows](https://docs.anaconda.com/miniconda/)
   - 시스템 Python 대신 프로젝트별 Conda 환경으로 Python 3.12와 패키지를
     분리한다.
3. [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
   - WSL 2 사용을 권장한다.
4. 선택: [Visual Studio Code](https://code.visualstudio.com/)

Docker Desktop이 WSL 설치를 요구하면 관리자 PowerShell에서 한 번 실행하고
재부팅한다.

```powershell
wsl --install
```

설치가 끝난 뒤 새 PowerShell을 열어 다음 네 명령이 모두 동작하는지 확인한다.

```powershell
git --version
conda --version
docker version
docker run --rm hello-world
```

마지막 명령은 Docker가 실제 컨테이너를 실행할 수 있는지 확인한다. 처음에는
이미지를 내려받느라 시간이 걸릴 수 있다.

`conda`가 "명령을 찾을 수 없습니다"라고 나오면 일반 PowerShell에서 다음 명령을
억지로 입력하지 않는다. 시작 메뉴에서 **Miniconda Prompt**를 열고 아래 한 줄을 실행한
뒤, 그 창을 닫고 새 PowerShell을 연다.

```powershell
conda init powershell
```

새 PowerShell에서 `conda --version`을 다시 실행한다. 여전히 찾을 수 없거나
Miniconda Prompt 자체가 없다면 Miniconda 설치가 끝나지 않은 것이므로 2.2의 설치 링크로
돌아가 설치를 다시 완료한다.

`conda`는 보이는데 `conda activate`가 동작하지 않으면 다음을 **한 번만** 실행하고
PowerShell을 완전히 닫았다가 새로 연다.

```powershell
conda init powershell
conda config --set auto_activate_base false
```

두 번째 명령은 새 PowerShell에서 `(base)`가 자동으로 시작하지 않게 한다. 이후
프로젝트 환경인 `(autoforge)`만 직접 활성화한다.

## 3. Docker를 안전하게 정리하는 방법

처음 설치한 컴퓨터라면 이 절은 건너뛴다. 기존에 만든 서버를 정리할 때도
전역 삭제 명령을 바로 쓰지 않는다.

현재 상태는 항상 먼저 확인한다.

```powershell
docker ps -a
docker volume ls
```

특정 로그인 서버만 멈추고 컨테이너와 네트워크만 지우려면 생성 서버 폴더에서
다음을 실행한다. DB와 Redis의 데이터 볼륨은 남는다.

```powershell
Set-Location C:\workspace\login-server
docker compose --env-file environment\.env -f environment\compose.integration.yml down --remove-orphans
```

계정을 포함한 **이 로그인 서버의 로컬 데이터까지 전부 초기화**하려면 다음을
쓴다. 이 명령은 되돌릴 수 없다.

```powershell
docker compose --env-file environment\.env -f environment\compose.integration.yml down --volumes --remove-orphans
```

`docker system prune --all --volumes`는 다른 프로젝트의 이미지와 볼륨도 지울 수
있으므로 이 가이드의 명령으로 사용하지 않는다.

## 4. AutoForge 설치와 첫 확인

PowerShell에서 AutoForge를 내려받고 독립된 Conda 환경을 만든다.

```powershell
New-Item -ItemType Directory -Force C:\src, C:\workspace | Out-Null
git clone https://github.com/AshOne91/AutoForge.git C:\src\AutoForge
Set-Location C:\src\AutoForge
conda create -n autoforge python=3.12 -y
conda activate autoforge
python --version
python -m pip install --upgrade pip
python -m pip install -e ".[test,server]"
```

`(autoforge)`가 PowerShell 프롬프트 앞에 보이고 `python --version`이 `Python 3.12`
로 시작하면 올바른 환경이 활성화된 것이다. `base` 환경에 AutoForge를 설치하지
않는다.

다음으로 생성기와 핵심 명세 테스트를 확인한다.

```powershell
python -m autoforge.main version
python -m pytest tests/core/test_specification_models.py -q
```

문제가 생기면 다음을 먼저 확인한다.

```powershell
python --version
conda env list
docker version
```

Python 3.12가 아니라면 `conda activate autoforge`가 빠졌거나 환경 생성이 실패한
것이다. 먼저 `conda env list`에서 `autoforge` 환경이 있는지 확인한다. 문제가
계속되면 AutoForge 저장소는 그대로 두고 `autoforge` Conda 환경만 다시 만든다.

## 5. 로그인 서버 명세 파일 만들기

명세 폴더와 specifications 폴더를 만든다.

```powershell
New-Item -ItemType Directory -Force C:\workspace\login-server-spec\specifications
New-Item -ItemType File -Force `
  C:\workspace\login-server-spec\autoforge.yaml, `
  C:\workspace\login-server-spec\specifications\identity.yaml, `
  C:\workspace\login-server-spec\specifications\system.yaml | Out-Null
```

VS Code를 설치했다면 다음으로 세 파일을 한 번에 연다.

```powershell
code C:\workspace\login-server-spec
```

`code` 명령을 찾을 수 없고 VS Code를 설치하지 않았다면, 아래처럼 Windows 기본
Notepad로 한 파일씩 연다. 각 파일에 이 절의 YAML 전체를 붙여 넣고 `Ctrl+S`로 저장한다.

```powershell
notepad C:\workspace\login-server-spec\autoforge.yaml
notepad C:\workspace\login-server-spec\specifications\identity.yaml
notepad C:\workspace\login-server-spec\specifications\system.yaml
```

세 파일 모두 이미 만들어졌으므로, 어떤 편집기를 쓰든 새 이름을 입력하거나 확장자를
바꿀 필요는 없다. YAML 들여쓰기는 탭이 아니라 공백을 사용한다.

### 5.1 `autoforge.yaml`

`C:\workspace\login-server-spec\autoforge.yaml`:

```yaml
spec_version: "1"

project:
  name: Login Server
  package_name: login_server
  version: "0.1.0"
  description: Beginner login-server foundation

tooling:
  docker:
    enabled: true
  local_environment:
    enabled: true
    application_enabled: true
    host_port_base: 49300

application:
  framework: fastapi
  modules:
    - identity
    - system
  services:
    - name: session
      kind: redis_session
      namespace: login_server_session
      ttl_seconds: 3600
  databases:
    - name: identity
      global_url_env: IDENTITY_DATABASE_URL
```

이 파일은 전체 서버 조합을 설명한다.

- `host_port_base: 49300`: 브라우저가 접속할 서버 포트는 `49300`이 된다.
- `identity`: 로그인 계정 모듈이다.
- `system`: ping/pong 확인 모듈이다.
- `redis_session`: 로그인 토큰을 Redis에 저장한다.
- `identity` DB: 계정 원장을 한 PostgreSQL 데이터베이스에 저장한다.

처음에는 사용자 샤딩, RabbitMQ, Nginx, 복제본을 넣지 않는다. 나중에 서버를
키울 때도 Router와 handler는 Redis/DB의 실제 토폴로지를 직접 알지 않는다.

### 5.2 `specifications/identity.yaml`

`C:\workspace\login-server-spec\specifications\identity.yaml`:

```yaml
spec_version: "1"

module:
  name: identity
  display_name: Identity
  route_prefix: /api/identity

models:
  - name: LoginAccount
    fields:
      - name: user_id
        type:
          kind: uuid
      - name: email
        type:
          kind: string
      - name: password_hash
        type:
          kind: string
      - name: is_active
        type:
          kind: boolean
        default: true
      - name: created_at
        type:
          kind: datetime

endpoints:
  - name: signup
    method: POST
    path: /signup
    request:
      fields:
        - name: email
          type:
            kind: string
        - name: password
          type:
            kind: string
    response:
      fields:
        - name: user_id
          type:
            kind: uuid
        - name: email
          type:
            kind: string
        - name: is_active
          type:
            kind: boolean
    handler: signup
    dependencies:
      - database_session_registry
  - name: login
    method: POST
    path: /login
    request:
      fields:
        - name: email
          type:
            kind: string
        - name: password
          type:
            kind: string
    response:
      fields:
        - name: user_id
          type:
            kind: uuid
        - name: access_token
          type:
            kind: string
        - name: token_type
          type:
            kind: string
    handler: login
    dependencies:
      - session_store
      - database_session_registry
  - name: validate_session
    method: POST
    path: /session/validate
    request:
      fields:
        - name: access_token
          type:
            kind: string
    response:
      fields:
        - name: user_id
          type:
            kind: uuid
    handler: validate_session
    dependencies:
      - session_store

database:
  provider: agnostic
  tables:
    - name: login_accounts
      columns:
        - name: user_id
          type:
            kind: uuid
          primary_key: true
        - name: email
          type:
            kind: string
          unique: true
        - name: password_hash
          type:
            kind: string
        - name: is_active
          type:
            kind: boolean
          default: true
        - name: created_at
          type:
            kind: datetime
  repositories:
    - name: LoginAccountRepository
      aggregate: LoginAccount
      table: login_accounts
      operations:
        - find_by_id
        - save
      queries:
        - name: find_by_email
          column: email
  placements:
    - table: login_accounts
      store: identity
      mode: global
      unresolved_policy: error
```

이 명세는 다음을 동시에 만든다.

```text
LoginAccount Python 모델
PostgreSQL login_accounts 테이블
SQLAlchemy repository
Alembic migration과 raw SQL
FastAPI request/response schema
FastAPI Router
비어 있는 signup/login/validate_session handler
```

### 5.3 `specifications/system.yaml`

`C:\workspace\login-server-spec\specifications\system.yaml`:

```yaml
spec_version: "1"

module:
  name: system
  display_name: System
  route_prefix: /api/system

endpoints:
  - name: ping
    method: GET
    path: /ping
    response:
      fields:
        - name: message
          type:
            kind: string
    handler: ping
```

Ping은 로그인과 무관한 시스템 확인 기능이므로 별도 모듈에 둔다. 이 서버의
첫 HTTP 계약은 `GET /api/system/ping → {"message":"pong"}`이다.

## 6. AutoForge로 서버 생성하기

AutoForge 가상환경이 활성화된 PowerShell에서 다음을 실행한다.

```powershell
Set-Location C:\src\AutoForge
python -m autoforge.main generate `
  --project C:\workspace\login-server-spec\autoforge.yaml `
  --specifications C:\workspace\login-server-spec\specifications `
  --output C:\workspace\login-server
```

성공하면 `Generated and validated` 문구가 나온다. 오류가 나면 YAML 들여쓰기,
이름, 포트 범위를 먼저 확인한다. 생성기 코드를 고치거나 생성 결과를 손으로
만들지 않는다.

생성된 서버도 같은 Conda 환경에 설치한다. 이 단계는 AutoForge를 다시 설치하는 것이
아니라, 방금 명세에서 선택된 서버 의존성(예: OpenAI client)을 테스트 Python이 읽게 하는
단계다. 이후 명세에 새 선택 서비스를 추가해 다시 생성했다면 이 명령도 한 번 더 실행한다.

```powershell
Set-Location C:\workspace\login-server
python -m pip install -e ".[test]"
```

이 명령은 아직 서버를 **실행하지 않는다**. `C:\workspace\login-server`에 실행할
서버의 파일을 만들 뿐이다. 다음 단계에서 `handlers.py`를 작성하고 Docker를 시작한다.

이후 생성 서버의 구조는 대략 다음과 같다.

```text
C:\workspace\login-server
├── environment/                 # Compose와 .env.example
├── migrations/                  # 생성된 DB migration
├── src/login_server/
│   ├── infrastructure/          # DB, Redis session 연결
│   └── modules/
│       ├── identity/
│       │   ├── generated/       # 생성 소유
│       │   └── handlers.py      # 여러분이 구현
│       └── system/
│           ├── generated/       # 생성 소유
│           └── handlers.py      # 여러분이 구현
└── Dockerfile
```

## 7. 생성 파일과 직접 작성 파일 구분

| 범위 | 예시 | 누가 수정하는가 |
| --- | --- | --- |
| GENERATED | `modules/*/generated/`, raw SQL, Alembic 환경, Compose | 명세를 고친 뒤 AutoForge 재생성 |
| SCAFFOLDED | `modules/*/handlers.py`, 최초 Alembic baseline (`migrations/*/versions/0001_*.py`) | 여러분 |
| 운영 설정 | `environment/.env` | 서버 운영자, Git에 올리지 않음 |
| 명세 | `login-server-spec/*.yaml` | 여러분 |

`generated/router.py`에 로그인 코드를 직접 쓰지 않는다. 재생성하면 사라질 수
있다. handler에 로그인 규칙을 쓰고, DB 테이블을 바꾸고 싶으면 YAML 명세부터
바꾼다.

## 8. Docker 환경 파일 만들기

생성 서버에서 예제 환경 파일을 복사한다.

```powershell
Set-Location C:\workspace\login-server
Copy-Item environment\.env.example environment\.env
```

처음에는 `environment/.env`의 기본 개발값을 그대로 쓸 수 있다.

```dotenv
LOCAL_BIND_ADDRESS=127.0.0.1
POSTGRES_USER=autoforge
POSTGRES_PASSWORD=change-me
POSTGRES_PORT=49310
REDIS_URL=redis://redis:6379
APPLICATION_PORT=49300
```

`redis`는 Docker Compose 내부 서비스 이름이다. 컨테이너끼리는 이 이름으로
통신하며, Redis를 호스트 포트로 공개할 필요가 없다. `change-me`는 내 컴퓨터의
첫 실습용일 뿐이며 인터넷에 노출하거나 실서비스에서 사용하면 안 된다.

Compose를 시작하기 전, 포트 충돌만 읽기 전용으로 검사한다.

```powershell
Set-Location C:\src\AutoForge
python -m autoforge.main validate-ports `
  --env-file C:\workspace\login-server\environment\.env
```

`49300`이 이미 사용 중이면 `autoforge.yaml`의 `host_port_base`를 다른 100단위
사설 포트 블록(예: `49400`)으로 바꾸고 다시 생성한다. 포트 규칙의 이유는
[로컬 포트 정책](../architecture/local_port_policy.md)에 있다.

이 검사는 명세와 `.env` 안에서 서로 겹치는 포트를 찾는 **사전 검사**다. Windows/WSL이
예약한 포트 범위는 Docker 시작 때만 거절될 수 있다. `ports are not available` 오류가
나면 generated Compose 파일을 직접 고치지 말고, 아래로 예약 범위를 확인한 뒤
`host_port_base`를 다른 100 단위 블록으로 바꾸고 서버를 다시 생성한다.

```powershell
netsh interface ipv4 show excludedportrange protocol=tcp
```

재생성은 비밀값을 지우지 않기 위해 기존 `environment/.env`를 자동으로 바꾸지 않는다.
처음 실습처럼 `.env`에 보존할 값이 없다면, 재생성 뒤 예제 파일로 다시 만들 수 있다.

```powershell
Remove-Item environment\.env
Copy-Item environment\.env.example environment\.env
```

이미 비밀값을 넣었다면 `.env.example`과 비교하여 `APPLICATION_PORT`, `POSTGRES_PORT`처럼
바뀐 포트 값만 `.env`에 직접 반영한다. `environment/.env`는 운영자 소유 설정이고,
`compose.integration.yml`은 생성물이므로 직접 수정하지 않는다.

## 9. 가장 먼저 Ping/Pong 구현하기

생성 직후 `ping` handler는 일부러 `NotImplementedError`다. 다음 파일을 연다.

```text
C:\workspace\login-server\src\login_server\modules\system\handlers.py
```

내용을 다음처럼 바꾼다.

```python
from __future__ import annotations

from login_server.modules.system.generated.schemas import PingResponse


async def ping() -> PingResponse:
    return PingResponse(message="pong")
```

이것이 첫 번째 직접 작성 도메인 코드다. Router 경로, response schema, FastAPI
연결은 AutoForge가 이미 생성했으므로 직접 만들지 않는다.

간단한 단위 테스트도 만든다.

`C:\workspace\login-server\tests\test_system_ping.py`:

```python
import pytest

from login_server.modules.system.handlers import ping


@pytest.mark.anyio
async def test_ping_returns_pong() -> None:
    response = await ping()

    assert response.message == "pong"
```

테스트는 생성 서버 가상환경에서 실행한다.

생성 서버는 `pyproject.toml`의 `pythonpath = ["src"]` 설정 때문에 별도 설치 없이
아래 명령으로 자신의 `src/` 코드를 찾는다. `ModuleNotFoundError`가 나오면 현재 위치가
`C:\workspace\login-server`인지 먼저 확인한다.

```powershell
Set-Location C:\workspace\login-server
python -m pytest tests\test_system_ping.py -q
```

## 10. Docker로 서버 시작하고 Ping 확인하기

처음에는 이미지 빌드가 필요하므로 시간이 걸린다.

```powershell
Set-Location C:\workspace\login-server
docker compose --env-file environment\.env -f environment\compose.integration.yml up -d --build --wait
docker compose --env-file environment\.env -f environment\compose.integration.yml ps
```

정상 상태를 확인한다.

```powershell
Invoke-RestMethod -UseBasicParsing http://127.0.0.1:49300/health
Invoke-RestMethod -UseBasicParsing http://127.0.0.1:49300/api/system/ping
```

예상 응답은 다음과 같다.

```json
{"status":"ok"}
```

```json
{"message":"pong"}
```

오류가 나면 로그는 이 순서로 본다.

```powershell
docker compose --env-file environment\.env -f environment\compose.integration.yml logs application --tail 100
docker compose --env-file environment\.env -f environment\compose.integration.yml logs postgres --tail 100
docker compose --env-file environment\.env -f environment\compose.integration.yml logs redis --tail 100
```

handler를 수정한 뒤에는 이미지에 코드를 다시 넣어야 한다.

```powershell
docker compose --env-file environment\.env -f environment\compose.integration.yml up -d --build application
```

## 11. 비밀번호를 평문으로 저장하지 않기

비밀번호를 DB에 그대로 저장하면 안 된다. 먼저 SCAFFOLDED 파일을 하나 만든다.

`C:\workspace\login-server\src\login_server\modules\identity\passwords.py`:

```python
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 600_000
SALT_BYTES = 16


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, ITERATIONS
    )
    return "$".join(
        (
            ALGORITHM,
            str(ITERATIONS),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        )
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = encoded.split("$")
        if algorithm != ALGORITHM:
            return False
        iterations = int(iterations_text)
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
    except (ValueError, UnicodeEncodeError):
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return hmac.compare_digest(actual, expected)
```

`salt`는 같은 비밀번호라도 매번 다른 hash를 만들고, `compare_digest`는 비교 시간을
일정하게 만들어 단순 문자열 비교보다 안전하다. 해시 함수는 CPU 작업이므로 다음
handler에서는 `asyncio.to_thread`로 이벤트 루프 밖에서 실행한다.

테스트를 먼저 만든다.

`C:\workspace\login-server\tests\test_passwords.py`:

```python
from login_server.modules.identity.passwords import hash_password, verify_password


def test_password_hash_verifies_only_the_original_password() -> None:
    encoded = hash_password("correct horse battery staple")

    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong password", encoded)
```

```powershell
python -m pytest tests\test_passwords.py -q
```

## 12. 회원가입·로그인·세션 검증 구현하기

다음 SCAFFOLDED 파일을 연다.

```text
C:\workspace\login-server\src\login_server\modules\identity\handlers.py
```

내용을 다음으로 교체한다.

```python
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException, status

from login_server.infrastructure.database.routing import ShardTarget
from login_server.infrastructure.database.session import AsyncSessionRegistry
from login_server.infrastructure.session_store.protocol import (
    SessionData,
    SessionStore,
    create_session_id,
)
from login_server.modules.identity.generated.models import LoginAccount
from login_server.modules.identity.generated.schemas import (
    LoginRequest,
    LoginResponse,
    SignupRequest,
    SignupResponse,
    ValidateSessionRequest,
    ValidateSessionResponse,
)
from login_server.modules.identity.generated.sqlalchemy_repositories import (
    SQLAlchemyLoginAccountRepository,
)
from login_server.modules.identity.passwords import hash_password, verify_password

IDENTITY_TARGET = ShardTarget(store="identity")


async def signup(
    request: SignupRequest,
    session_registry: AsyncSessionRegistry,
) -> SignupResponse:
    email = request.email.strip().lower()
    async with session_registry.session(IDENTITY_TARGET) as session:
        repository = SQLAlchemyLoginAccountRepository(session)
        if await repository.find_by_email(email) is not None:
            raise HTTPException(status_code=409, detail="Email is already registered")
        account = LoginAccount(
            user_id=uuid4(),
            email=email,
            password_hash=await asyncio.to_thread(hash_password, request.password),
            is_active=True,
            created_at=datetime.now(UTC),
        )
        await repository.save(account)
    return SignupResponse(
        user_id=account.user_id,
        email=account.email,
        is_active=account.is_active,
    )


async def login(
    request: LoginRequest,
    session_store: SessionStore,
    session_registry: AsyncSessionRegistry,
) -> LoginResponse:
    email = request.email.strip().lower()
    async with session_registry.session(IDENTITY_TARGET) as session:
        account = await SQLAlchemyLoginAccountRepository(session).find_by_email(email)
    valid_password = account is not None and await asyncio.to_thread(
        verify_password, request.password, account.password_hash
    )
    if account is None or not account.is_active or not valid_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token = create_session_id(str(account.user_id))
    await session_store.create(
        SessionData(session_id=access_token, user_id=str(account.user_id), data={})
    )
    return LoginResponse(
        user_id=account.user_id,
        access_token=access_token,
        token_type="bearer",
    )


async def validate_session(
    request: ValidateSessionRequest,
    session_store: SessionStore,
) -> ValidateSessionResponse:
    session = await session_store.get(request.access_token)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    return ValidateSessionResponse(user_id=UUID(session.user_id))
```

이 코드는 다음 책임만 가진다.

| 함수 | 책임 |
| --- | --- |
| `signup` | 중복 이메일을 막고 password hash와 계정을 DB에 저장 |
| `login` | DB에서 계정을 찾고 password hash를 확인한 뒤 Redis 세션 생성 |
| `validate_session` | Redis에서 토큰을 읽고 로그인한 사용자 ID 반환 |

DB의 계정 행과 Redis 세션은 역할이 다르다. 계정은 PostgreSQL에 오래 남고, 로그인
토큰은 Redis TTL이 끝나면 사라진다. Redis가 계정의 원장이 되면 안 된다.

## 13. 회원가입부터 세션 확인까지 실제로 테스트하기

handler를 구현한 뒤 이미지를 다시 빌드한다.

```powershell
Set-Location C:\workspace\login-server
python -m pytest tests\test_system_ping.py tests\test_passwords.py -q
docker compose --env-file environment\.env -f environment\compose.integration.yml up -d --build --wait
```

회원가입 요청을 보낸다.

```powershell
$signupBody = @{ email = "chimp@example.com"; password = "local-only-password" } | ConvertTo-Json
Invoke-RestMethod -UseBasicParsing `
  -Method Post `
  -Uri http://127.0.0.1:49300/api/identity/signup `
  -ContentType "application/json" `
  -Body $signupBody
```

같은 이메일로 다시 회원가입하면 `409` 오류가 나야 한다. 이는 DB의 unique 제약과
handler의 사전 확인이 함께 동작한다는 뜻이다.

PowerShell이 `409`을 오류로 표시하는 것은 정상이다. 아래 명령은 그 오류가 정확히
`409`인지 확인하고, 다른 오류라면 멈춘다.

```powershell
try {
  Invoke-RestMethod -UseBasicParsing `
    -Method Post `
    -Uri http://127.0.0.1:49300/api/identity/signup `
    -ContentType "application/json" `
    -Body $signupBody `
    -ErrorAction Stop | Out-Null
  throw "같은 이메일 가입이 잘못 성공했습니다."
} catch {
  if ($_.Exception.Response.StatusCode.value__ -ne 409) { throw }
  "중복 가입이 409로 차단되었습니다."
}
```

로그인하고 반환 토큰을 변수에 저장한다.

```powershell
$login = Invoke-RestMethod -UseBasicParsing `
  -Method Post `
  -Uri http://127.0.0.1:49300/api/identity/login `
  -ContentType "application/json" `
  -Body $signupBody

$login
```

세션을 검증한다.

```powershell
$sessionBody = @{ access_token = $login.access_token } | ConvertTo-Json
Invoke-RestMethod -UseBasicParsing `
  -Method Post `
  -Uri http://127.0.0.1:49300/api/identity/session/validate `
  -ContentType "application/json" `
  -Body $sessionBody
```

마지막으로 애플리케이션만 재시작한 뒤 같은 토큰을 다시 검증한다.

```powershell
docker compose --env-file environment\.env -f environment\compose.integration.yml restart application

# restart는 컨테이너를 다시 시작했을 뿐, FastAPI가 준비됐다는 뜻은 아니다.
$health = $null
$deadline = (Get-Date).AddSeconds(30)
do {
  try {
    $health = Invoke-RestMethod -UseBasicParsing -Uri http://127.0.0.1:49300/health -ErrorAction Stop
    if ($health.status -eq "ok") { break }
  } catch {}
  Start-Sleep -Seconds 1
} while ((Get-Date) -lt $deadline)

if ($null -eq $health -or $health.status -ne "ok") {
  throw "30초 안에 application이 준비되지 않았습니다."
}

Invoke-RestMethod -UseBasicParsing `
  -Method Post `
  -Uri http://127.0.0.1:49300/api/identity/session/validate `
  -ContentType "application/json" `
  -Body $sessionBody
```

두 번째 검증도 성공하면 FastAPI 프로세스가 재시작되어도 Redis 세션이 유지되는 것을
확인한 것이다.

## 14. 테스트를 읽는 순서

처음에는 다음 순서만 지킨다.

```text
1. 명세 생성 명령의 validation 통과
2. 순수 함수 테스트: password hash
3. 작은 handler 테스트: ping
4. Docker health
5. 실제 HTTP: signup → login → validate session
6. application 재시작 뒤 validate session
```

테스트가 실패하면 전체 `pytest`부터 실행하지 않는다. 실패한 명령의 오류와 해당
handler 또는 `.env`를 먼저 본다. Docker가 멈췄다면 `docker version`, 컨테이너가
멈췄다면 `docker compose ... ps`와 `logs`를 확인한다.

## 15. 로그와 데이터는 어디에 남는가

| 대상 | 위치 | 지워지는 시점 |
| --- | --- | --- |
| 애플리케이션 로그 | 생성 서버의 `logs/` | 직접 삭제하거나 보존 정책 적용 시 |
| PostgreSQL 계정 | PostgreSQL named volume | `down --volumes` 실행 시 |
| Redis 세션 | Redis named volume과 TTL | TTL 만료 또는 Redis 데이터 초기화 시 |
| `.env` 비밀값 | 로컬 파일 | 직접 삭제 시 |

`.env`와 `logs/`는 Git에 올리지 않는다. 코드와 환경 설정과 런타임 데이터는 서로
다른 것이며, 자세한 이유는 [설정·저장소 정책](../architecture/configuration_and_storage_policy.md)을
참고한다.

## 16. 단일 모드가 완성된 뒤 HA 모드로 가는 법

첫 로그인 서버가 단일 모드에서 모두 통과하기 전에는 HA를 켜지 않는다. 단일 모드는
개발 속도를 위한 기본값이고, 지금 작성한 handler는 PostgreSQL/Redis의 실제 주소나
복제본 수를 알지 않는다. 그래서 나중에 다음처럼 인프라만 확장할 수 있다.

```text
단일 모드
클라이언트 → FastAPI 1개 → PostgreSQL 1개 / Redis 1개

단일 물리 서버 HA 모드
클라이언트 → Nginx → FastAPI 여러 개 → PostgreSQL HA / Redis Cluster
```

HA용 명세는 기본 명세를 복사한 `autoforge.ha.yaml`로 별도 관리한다. 다음 변경만
추가한다.

- `tooling.local_environment.postgres_mode: ha`
- `tooling.single_host.enabled: true`
- `tooling.single_host.application_replicas: 2` 이상
- Redis session service의 `mode: cluster`와 `cluster_url_env: REDIS_CLUSTER_URL`
- 기본 포트와 겹치지 않는 `host_port_base` (예: `49400`)

HA 검증은 기본 서버와 **별도 output 폴더, 별도 Compose project, 별도 볼륨**에서
수행한다. 기존 단일 서버의 볼륨을 지워서 HA 테스트를 시작하지 않는다. 이 단계의
정확한 보장과 한계는 [환경 검증 계약](../architecture/environment_validation_contract.md)에
있다. 한 대의 PC에서 HA를 검증하는 것은 컨테이너·서비스 장애 복구 검증이지,
물리 서버나 가용 영역 장애에 대한 보장은 아니다.

## 17. 다음 도메인 작업 순서

로그인 서버가 끝난 뒤에는 한 번에 기능을 많이 넣지 않는다.

실제 공통 서비스 선택부터 `내 프로필` 도메인을 테스트하는 다음 실습은
[도메인·공통 서비스 실습](domain_service_workbook.md)을 따른다.

1. 로그아웃: Redis `revoke`로 현재 세션을 지운다.
2. 내 정보: 로그인된 사용자만 자기 프로필을 읽고 수정한다.
3. 권한: `user`, `operator` 같은 접근 수준을 명세와 세션에 연결한다.
4. 이메일 인증 또는 비밀번호 재설정: 외부 전달 수단을 정한 뒤 추가한다.
5. 비동기 메시지: 실제로 요청 밖에서 실행할 일이 생긴 뒤 RabbitMQ/Outbox를 선택한다.
6. WebSocket: 실시간 양방향 기능이 필요한 경우에만 Ping/Pong을 추가한다.

HTTP `GET /api/system/ping`은 서버가 요청에 답하는지 확인하는 첫 단계다. WebSocket
Ping/Pong은 연결 유지와 실시간 메시지용 별도 계약이므로, HTTP 로그인 흐름이
안정된 뒤 다룬다.

## 18. 막혔을 때 확인표

| 증상 | 먼저 볼 곳 | 흔한 원인 |
| --- | --- | --- |
| `conda` 명령이 없음 | Miniconda 설치 | 설치 뒤 PowerShell을 새로 열지 않음 |
| `conda activate autoforge` 실패 | `conda init powershell`, `conda env list` | shell 초기화 또는 환경 생성 누락 |
| `python --version`이 3.12가 아님 | `conda activate autoforge` | base/다른 환경이 활성화됨 |
| Docker 연결 오류 | Docker Desktop | Desktop/WSL이 아직 시작되지 않음 |
| 생성 명령 실패 | YAML | 들여쓰기, 모듈 이름, 포트 범위 오류 |
| Compose가 시작되지 않음 | `environment/.env` | 필수 값 누락 또는 포트 충돌 |
| `/health`가 503 | `docker compose logs application` | PostgreSQL 또는 Redis 준비 실패 |
| `/ping`이 500 | `system/handlers.py` | `NotImplementedError`를 아직 교체하지 않음 |
| 로그인 500 | `identity/handlers.py`와 PostgreSQL 로그 | handler import, migration, DB 연결 오류 |
| 로그인 뒤 세션 검증 401 | Redis 로그와 토큰 값 | 잘못된 토큰, TTL 만료, Redis 초기화 |

## 19. 더 깊게 볼 정본 문서

이 가이드를 한 번 끝낸 뒤 아래 문서를 읽는다. 같은 내용을 다시 정의하지 않고,
각 문서는 하나의 사실을 소유한다.

- [전체 생성 흐름](../architecture/system_design.md)
- [YAML 명세의 모든 필드](../architecture/specification_design.md)
- [생성 파일과 SCAFFOLDED 파일의 소유권](../architecture/generation_contract.md)
- [PostgreSQL·SQL·Repository·Global/Shard](../architecture/database_generation.md)
- [Redis 세션과 TTL](../architecture/redis_services.md)
- [로그·헬스체크·관측성](../architecture/observability_generation.md)
- [포트 정책](../architecture/local_port_policy.md)
- [도메인과 공통 서비스를 조합하는 실습](domain_service_workbook.md)

이 문서의 첫 목표는 완벽한 서비스가 아니라, 여러분이 명세를 바꾸고 생성하고
handler를 작성하고 테스트하는 한 바퀴를 스스로 완주하는 것이다.
