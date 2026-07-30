# AutoForge 프로젝트 가이드

- 기준일: 2026-07-29
- 최종 갱신일: 2026-07-30
- 프로젝트 버전: 0.1.0
- Python: 3.12 이상
- 문서 대상: 프로젝트 개발자, 리뷰어, 후속 작업을 수행하는 AI Agent

## 1. 이 문서의 목적

이 문서는 AutoForge의 목표, 현재 구조, 설계 이유, 구현 상태와 다음 작업을
한곳에서 설명한다. 새로운 개발자나 AI는 코드를 변경하기 전에 이 문서와
`AGENTS.md`, `.codex/` 문서를 함께 읽어야 한다.

이 문서에서 사용하는 상태 표현은 다음과 같다.

- 구현 완료: 현재 소스와 pytest로 확인된 기능
- 부분 구현: 계약이나 기반만 있고 실제 실행 흐름은 완성되지 않은 기능
- 예정: Roadmap에는 있지만 아직 코드가 없는 기능

## 2. AutoForge가 해결하려는 문제

게임 서버나 웹서버를 개발하면 다음 코드가 반복된다.

- 프로젝트와 패키지 기본 구조
- Application 진입점
- 설정과 로깅
- API Request/Response 모델
- Router와 Handler 연결
- Domain Model
- Service와 Repository 골격
- DB Schema와 Migration
- 테스트
- Docker와 CI/CD 설정

AutoForge는 검증된 명세로 이 반복 코드를 생성하고, 사용자 코드를 보존하며,
생성 결과를 테스트한 뒤 안전한 변경만 Git에 반영하는 자동화 플랫폼을
목표로 한다.

최종 흐름은 다음과 같다.

```text
Git Event 또는 CLI
  → Project/Module Specification
  → GenerationJob
  → 격리된 Workspace
  → GenerationPlan
  → Generator
  → GenerationManifest
  → Test / Lint / Build Pipeline
  → 검증 성공
  → Commit / Push / Pull Request
```

현재는 로컬 명세 기반 생성과 안전한 계획 수립을 먼저 구현하고 있다.

## 3. 참고 프로젝트와 계승한 개념

### 3.1 common-tool

참고 경로:

```text
C:\게임베이스툴\common-tool-master
```

확인된 C# Generator:

- GenerateApplication
- GenerateTemplate
- GenerateController
- GenerateDatabase
- GenerateSql
- GenerateTable

`common-tool`은 설정과 명령을 받아 Application, Template, Packet, Protocol,
Controller, DB 코드와 SQL을 빠르게 생성한다. 반복 작업을 줄이는 목적과
생성기 중심 접근은 AutoForge가 계승한다.

그대로 가져오지 않은 부분:

- 파일을 직접 덮어쓰는 방식
- 생성 코드와 사용자 코드가 섞이는 구조
- 강한 경로 및 프로젝트 결합
- 검증 전 파일 변경
- Plugin, Event, Pipeline 부재
- Git과 CI/CD 안전 정책 부재

### 3.2 game-server

참고 경로:

```text
C:\게임베이스서버\game-server-master
```

`common-tool`로 생성된 Application, Controller, Template, Common Packet,
Protocol, Model, DB 코드와 사용자가 추가한 비즈니스 로직을 확인했다.

계승한 책임 분리:

```text
Application
  → 서버 조립과 생명주기

Template
  → Account, Item, Shop 같은 도메인 기능

Common
  → Packet, Protocol, Model

Controller
  → Application과 Template 연결
```

C#의 `partial class`는 생성 코드와 사용자 구현을 나누는 데 사용됐다.
Python에는 동일한 기능이 없으므로 AutoForge는 파일 소유권으로 대체한다.

### 3.3 base_server

참고 경로:

```text
C:\SKN12-FINAL-2TEAM\base_server
```

FastAPI Application, Router, Template, Service, 설정, lifespan, Docker와
CI/CD 구성의 실제 사례를 참고한다.

계승한 방향:

- Application과 Router 분리
- 도메인 Template 분리
- DB, Cache, Queue, Storage 같은 Service 분리
- 비동기 Handler와 lifespan
- Pydantic 기반 Request/Response

그대로 복사하지 않는 부분:

- 거대한 단일 `main.py`
- import 시 전역 Service 초기화
- 프로젝트 전용 금융, 채팅, AI 기능
- 전역 ServiceContainer 의존
- 환경별 비밀정보가 포함된 설정

AutoForge가 생성할 서버는 `base_server`의 유용한 책임 경계를 유지하면서
더 작고 모듈형이며 반복 생성에 안전해야 한다.

### 3.4 SKN12-FINAL-2TEAM과 kis-auto-trading

사용자가 확정한 제품 관계는 다음과 같다.

```text
common-tool + game-server
  → 반복 코드 생성 방식의 원형

SKN12-FINAL-2TEAM
  → 서비스 기능과 수작업 이벤트, 큐, Kubernetes 구현의 원형

AutoForge
  → 반복 구조를 명세 기반으로 생성하고 검증하는 플랫폼

kis-auto-trading
  → SKN12 기능을 현대적인 구조로 재구성할 첫 실제 생성 대상
```

AutoForge는 SKN12를 파일 단위로 복사하지 않는다.

- 반복되는 구조와 연결 코드는 Specification과 Generator로 만든다.
- 이벤트, 큐, 배포 기술은 Protocol, Adapter와 Plugin 경계로 현대화한다.
- 매매 전략처럼 프로젝트 고유한 비즈니스 로직은 사용자 소유 코드로 둔다.
- 생성 코드와 사용자 코드는 파일 소유권으로 분리한다.
- 실제 코드를 확인하지 않은 기능은 구현 사실로 가정하지 않는다.

향후 설계의 실용성은 `SKN12 → AutoForge → kis-auto-trading` 수직 흐름으로
검증한다.

## 4. 왜 C#을 Python으로 단순 포팅하지 않는가

목표는 기존 C# 코드의 문법 변환이 아니다.

```text
기존 방식
설정 → C# 파일 생성 → 사람이 직접 수정

AutoForge
버전이 있는 명세
  → 생성 계획
  → 소유권과 충돌 검사
  → 격리된 생성
  → 테스트와 빌드
  → Manifest
  → 검증된 Git 변경
```

Python/FastAPI 생태계에 맞게 다음을 다시 설계한다.

- C# partial class 대신 파일 소유권
- 프로젝트 참조 대신 Python package와 dependency
- Protocol/Packet을 HTTP/WebSocket/Queue Message로 일반화
- 동기 실행기 대신 async-first Task와 Pipeline
- 직접 Git 조작 대신 검증 이후 별도 Git Service

## 5. 현재 저장소 구조

```text
AutoForge/
├── .codex/                         Agent 작업 문서
├── docs/
│   ├── architecture/               상세 설계
│   ├── development/                개발 규칙
│   ├── release/                    변경 기록
│   └── PROJECT_GUIDE_2026-07-29.md 이 문서
├── src/autoforge/
│   ├── cli/                        Typer CLI
│   ├── core/                       핵심 계약과 정책
│   │   ├── config/
│   │   ├── context/
│   │   ├── event/
│   │   ├── generation/
│   │   ├── pipeline/
│   │   ├── plugin/
│   │   ├── registry/
│   │   ├── specification/
│   │   ├── task/
│   │   └── workspace/
│   ├── infrastructure/             외부 시스템 Adapter 예정
│   ├── models/                     기존 공통 결과 모델
│   ├── plugins/                    기본 Plugin Catalog 조립
│   └── services/
│       └── generation/             Generator와 계획 해석 Service
├── tests/
│   ├── cli/
│   ├── core/
│   └── services/
├── autoforge.yaml                  AutoForge 실행 설정 예시
├── environment.yml                 Conda 환경
└── pyproject.toml                  패키지와 도구 설정
```

빈 미래 디렉터리는 미리 만들지 않는다. Database, Git, Webhook, Plugin
구현 단계에 들어갈 때 Roadmap에 따라 소스와 테스트를 함께 만든다.

## 6. 계층별 책임

### CLI

사용자 입력과 출력만 담당한다. 생성 규칙이나 Git 로직을 직접 구현하지
않는다.

### Core

프레임워크에 독립적인 계약과 정책을 담당한다.

- Specification
- Generator Protocol
- GenerationPlan과 Manifest 모델
- 파일 소유권과 상태
- Workspace 경로 안전성
- Registry
- Event와 Task
- Plugin 기반 계약

### Services

하나의 유스케이스를 조합한다.

- FastAPI Project 렌더링
- GenerationPlan 생성
- Workspace 상태 기반 충돌 판정
- 향후 파일 적용, 검증, Build, Git 조정

### Infrastructure

파일시스템, 외부 Process, Git Provider, Webhook, Database처럼 외부 환경과
직접 통신하는 Adapter가 위치한다. 현재 비동기 외부 Process Runner와
작업별 격리 Workspace Manager가 구현되어 있다.

## 7. 현재 실행 흐름

구현된 범위:

```text
ProjectSpec
  → Pydantic 검증
  → FastAPIProjectGenerator.render()
  → 메모리에서 파일 내용 생성
  → FastAPIProjectGenerator.plan()
  → 파일별 Hash와 소유권 기록
  → GenerationPlanResolver.resolve()
  → Workspace의 기존 파일과 비교
  → CREATE / KEEP / SKIP / CONFLICT 확정
  → GenerationPlanApplier.apply()
  → 계획과 렌더링 결과 재검증
  → 충돌이 없으면 CREATE 파일 적용
  → 메모리 GenerationManifest 반환
```

검증까지 구현된 범위:

```text
생성된 프로젝트
  → ProjectValidator
  → 별도 Python 프로세스 Import 검증
  → 별도 pytest 프로세스 검증
  → Ruff lint 검증
  → wheel Package Build
  → stdout, stderr, 종료 코드, Timeout 결과
  ⇢ Git 반영
```

## 8. Specification이 필요한 이유

Specification은 생성할 서버의 검증 가능한 설계도다.

```python
ProjectSpec(
    spec_version="1",
    project=ProjectInfo(
        name="Game Server",
        package_name="game_server",
        version="0.1.0",
    ),
    application=ApplicationSpec(
        framework="fastapi",
        modules=["tutorial"],
    ),
)
```

CLI, YAML, Git Event, Web UI와 향후 AI가 각자 Generator를 직접 호출하지
않고 동일한 Specification을 만든다.

```text
YAML / CLI / Git Event / Web UI / AI
                  ↓
            Specification
                  ↓
              Generator
```

장점:

- 입력 방식과 Generator 분리
- 생성 전 잘못된 이름과 Type 차단
- 명세 버전 관리
- 동일 명세의 결정적 결과
- Plugin 호환성 검사 기반

## 9. 공통 Type System

첫 MVP가 지원하는 Type:

- string
- integer
- number
- boolean
- datetime
- uuid
- model
- list
- optional

예:

```python
FieldType(
    kind=FieldTypeKind.LIST,
    item=FieldType(
        kind=FieldTypeKind.MODEL,
        reference="ItemInfo",
    ),
)
```

공통 Type은 FastAPI에 직접 종속되지 않는다. Generator가 이를 Pydantic,
SQLAlchemy, JSON Schema 또는 DB Type으로 변환한다.

## 10. 파일 소유권

### GENERATED

명세로 완전히 재현할 수 있는 파일이다.

- Generator가 반복 생성 가능
- 사용자가 직접 수정하지 않는 영역
- 내용 Hash가 예상과 다르면 충돌

예:

```text
application/generated/module_registry.py
modules/tutorial/generated/schemas.py
modules/tutorial/generated/router.py
```

### SCAFFOLDED

최초 한 번만 생성하고 이후 사용자 파일로 보존한다.

예:

```text
README.md
modules/tutorial/handlers.py
modules/tutorial/service.py
```

### USER_OWNED

사용자가 직접 만든 파일이다. AutoForge는 생성하거나 변경하지 않는다.

## 11. GenerationPlan과 Manifest

### GenerationPlan

파일을 쓰기 전에 수행할 작업을 표현한다.

```text
CREATE
REPLACE_GENERATED
KEEP
SKIP
CONFLICT
```

각 PlannedFile은 다음을 가진다.

- Workspace 상대경로
- Generator ID와 버전
- 파일 소유권
- 예정 작업
- Specification Hash
- 예상 Content Hash
- 출처

### GenerationManifest

실제 실행 결과를 기록하는 모델과 Workspace 적용 결과를 Manifest로 변환하는
기능이 구현되어 있다. `ManifestStore`는 결과를
`.autoforge/manifest.json`에 결정적인 UTF-8 JSON으로 저장하고, 로딩할 때
Pydantic 모델로 다시 검증한다.

기록 상태:

```text
CREATED
CHANGED
UNCHANGED
PRESERVED
SKIPPED
CONFLICT
FAILED
```

Manifest는 향후 안전한 반복 생성과 감사 기록의 기준이 된다.

## 12. Workspace 안전 정책

Workspace는 AutoForge가 파일을 다룰 수 있는 유일한 경계다.

거부하는 경로:

```text
/absolute/file.py
C:/Windows/file.py
../outside.py
src/../../outside.py
src\windows\style.py
```

`Workspace.resolve()`는 해석된 경로가 root 밖으로 나가면 예외를 발생시킨다.

`IsolatedWorkspaceManager`는 작업 이름을 검증한 뒤 지정된 base 디렉터리
아래에 충돌하지 않는 임시 Workspace를 만든다. `async with` 범위가 끝나면
정상·예외 여부와 관계없이 자동 정리한다. 실패 자료를 조사해야 할 때만
`preserve_on_error=True`로 명시해 실패 Workspace를 보존한다.

현재 Resolver 정책:

| 상태 | 결과 |
|---|---|
| 대상 없음 | CREATE |
| GENERATED 내용 동일 | KEEP |
| GENERATED 내용 다름 | CONFLICT |
| SCAFFOLDED 존재 | KEEP |
| USER_OWNED 없음 | SKIP |
| USER_OWNED 존재 | KEEP |
| 파일 위치에 디렉터리 존재 | CONFLICT |

Resolver는 파일을 쓰거나 삭제하지 않는다.

`GenerationPlanApplier`는 Resolver 이후 다음을 다시 검증한다.

- 계획과 렌더링 경로의 완전한 일치
- 명세 Hash와 파일별 명세 Hash의 일치
- 렌더링 내용과 예상 Content Hash의 일치
- CONFLICT가 하나라도 있으면 쓰기 전 전체 중단
- 계획 이후 Workspace가 변경되지 않았는지 확인
- CREATE 파일의 결정적인 UTF-8 바이트 기록
- KEEP과 SKIP 파일 보존
- 파일별 결과를 메모리 GenerationManifest로 반환

`REPLACE_GENERATED`는 안전한 이전 Hash 계약이 정의되기 전까지 적용하지
않았으나, 현재는 이전 Manifest의 Generator ID, source, 소유권과 Content
Hash가 모두 일치할 때만 허용한다. 적용 직전에도 현재 파일 Hash를 다시
확인하고 결과를 CHANGED로 기록한다.

## 13. Plugin, Registry, EventBus, Task와 Pipeline

### Registry

이름과 객체를 연결하는 범용 저장소다. 중복 등록을 거부하고 이름을 정렬해
반환한다.

### PluginManager

현재 Plugin 등록, 조회, 실행과 해제를 담당한다. 내부 저장소로 Registry를
사용한다.

기존 Project/Module Generator는 렌더링 계약을 유지한다.
`GeneratorPluginAdapter`가 Plugin ID·버전·API 버전·Capability·지원
Specification 버전을 Metadata와 연결하고, 선언과 실제 Generator가
일치하는지 검증한다.

Plugin API v1은 버전이 있는 Plugin 의존성과 외부 자원 접근 권한도
Metadata로 선언한다. Capability는 제공 기능, Permission은 파일·Process·
Network 같은 외부 접근 권한이다. 자기 의존, 중복 의존성·권한과 지원하지
않는 API 버전은 등록 또는 Adapter 결합 전에 거부한다.

`PluginLoader`는 명시된 Plugin 루트 바로 아래 디렉터리의 `plugin.json`을
이름순으로 발견한다. 루트 밖을 가리키는 Symlink, 손상된 Manifest, 알 수
없는 필드·API 버전과 중복 Plugin ID를 거부한다. 이 발견 단계는 Plugin
Python 코드를 Import하거나 실행하지 않는다.

발견 후에는 기존 문자열 의존성과 버전형 의존성을 함께 해석한다. 누락,
정확한 버전 불일치와 순환을 거부하고 의존 Plugin이 먼저 오는 결정적인
순서를 계산한다. 의존성 정렬 단계도 Python 코드를 실행하지 않는다.

명시적인 `load_trusted()`만 `module:factory` Entrypoint를 Import한다.
Factory의 Plugin 계약과 Manifest Metadata 전체 일치를 확인하고 모든
인스턴스 생성이 성공한 뒤 의존성 순서로 PluginManager에 등록한다. 중간
등록 실패 시 이번 호출의 등록분을 Rollback한다. 이 API는 신뢰한 로컬
Plugin용이며 OS 수준 Sandbox를 제공하지 않는다.

`GeneratorPluginRegistry[SpecificationT]`는 ProjectSpec과 ModuleSpec용
Registry를 분리해 명세 타입을 보존한다. 현재 FastAPI Project Generator와
Module Generator가 실제 Metadata와 결합되어 Generator ID로 조회된다.

`ValidatorPluginRegistry[RequestT, ResultT]`는 비동기 요청·결과 타입을
보존한다. ProjectValidator는 Request Adapter를 통해 기존 Import, pytest,
Ruff와 wheel Build 동작을 유지하며 Metadata에 파일 읽기·쓰기와 Process
실행 권한을 선언한다.

`BuiltinPluginCatalog`는 기본 Project/Module Generator와 Project Validator
Registry를 Application 계층에 한 번에 전달한다. package name과
ProcessRunner를 명시적으로 주입하고 호출마다 새 Registry를 만들기 때문에
테스트나 여러 생성 작업 사이에서 전역 상태가 공유되지 않는다.

### PluginLoader

Plugin 검색, Metadata 호환성, Capability, 의존성 정렬, 권한 선언과 명시적인
trusted 로딩까지 구현되어 있다. Built-in Catalog가 기본 구현을 조립하는
경로와 외부 PluginLoader의 발견·로딩 경로는 의도적으로 분리한다. OS 수준
Sandbox와 실패 격리는 아직 구현되지 않았다.

### EventBus

EventBus는 AutoForge 주요 컴포넌트 사이의 중앙 통신 메커니즘이다. Event를
여러 비동기 Handler에 전달하지만 Git, Plugin, Generator와 Pipeline의 내부
구조나 업무 규칙을 알지 않는다.

Handler가 Event를 Application Service에 연결하고 처리 결과를 새 Event로
발행한다. EventBus는 중앙 통신 수단이지만 중앙 실행기는 아니다.

### Task와 Pipeline

Task 기본 계약과 TaskManager는 존재한다. Pipeline은 자리표시자 계약만
있으며 실행 순서, 재시도, Timeout과 실패 정책은 아직 구현되지 않았다.
장기적으로 Pipeline이 Job 내부의 Task 순서와 실패 정책을 명시적으로
소유한다. Handler 등록 순서나 Event 연쇄만으로 업무 순서를 숨기지 않는다.

Command는 실행 요청, Event는 이미 발생한 사실로 의미를 구분한다. 현재
EventBus는 Event만 다루므로 Command 전달 방식은 첫 GenerationPipeline
구현 전에 별도로 결정한다. 상세 결정은
`docs/architecture/event_driven_architecture.md`를 따른다.

현재 `ProjectValidator`는 Pipeline을 확정하지 않고 다음 네 단계를 순서대로
실행한다.

1. 생성 패키지의 `main` 모듈 Import
2. 생성 프로젝트의 pytest
3. 생성 프로젝트의 Ruff 검사
4. 격리된 `.autoforge/dist` 경로에 wheel Package Build

`AsyncioProcessRunner`는 shell을 사용하지 않고 인자 튜플로 프로세스를
실행하며 Workspace를 실행 디렉터리로 고정한다. 종료 코드, stdout, stderr,
실행 시간과 Timeout 여부를 구조화된 결과로 반환한다. Import가 실패하면
pytest를 실행하지 않는다.

## 14. 생성되는 최소 FastAPI 프로젝트

현재 `FastAPIProjectGenerator`는 메모리에서 다음 파일을 렌더링한다.

```text
generated-project/
├── pyproject.toml
├── README.md
├── src/<package_name>/
│   ├── __init__.py
│   ├── main.py
│   ├── application/
│   │   ├── __init__.py
│   │   └── app_factory.py
│   └── routers/
│       ├── __init__.py
│       └── health.py
└── tests/
    └── test_health.py
```

`main.py`는 얇게 유지한다.

```python
from game_server.application.app_factory import create_app

app = create_app()
```

비즈니스 로직이나 Service 초기화를 `main.py`에 넣지 않는다.

## 15. FastAPI 기본 문법

### FastAPI 애플리케이션

```python
from fastapi import FastAPI

app = FastAPI(title="Game Server", version="0.1.0")
```

`FastAPI` 객체는 ASGI 애플리케이션이다. Uvicorn이 이 객체를 실행한다.

### Application Factory

```python
def create_app() -> FastAPI:
    app = FastAPI(title="Game Server")
    app.include_router(health_router)
    return app
```

전역에서 모든 Service를 초기화하지 않고 함수가 Application을 조립하게 한다.
테스트마다 독립된 App을 만들거나 설정을 주입하기 쉬워진다.

### APIRouter

```python
from fastapi import APIRouter

router = APIRouter(prefix="/api/tutorial", tags=["tutorial"])
```

Router는 관련 Endpoint를 묶는 단위다.

### Endpoint Decorator

```python
@router.get("/progress")
async def get_progress() -> dict[str, int]:
    return {"step": 1}
```

`@router.get()`은 HTTP GET 경로를 함수에 연결한다.

### async def

```python
async def get_progress() -> dict[str, int]:
    ...
```

DB, Cache, HTTP 같은 I/O를 기다리는 동안 다른 요청을 처리할 수 있다.
CPU 연산이 자동으로 빨라지는 문법은 아니다.

### Pydantic Request와 Response

```python
from pydantic import BaseModel


class CompleteStepRequest(BaseModel):
    step: int


class ProgressResponse(BaseModel):
    current_step: int
    completed: bool
```

FastAPI는 Pydantic 모델로 JSON 입력을 검증하고 OpenAPI Schema를 만든다.

```python
@router.post("/complete", response_model=ProgressResponse)
async def complete_step(
    request: CompleteStepRequest,
) -> ProgressResponse:
    return ProgressResponse(
        current_step=request.step,
        completed=True,
    )
```

### Depends

```python
from typing import Annotated

from fastapi import Depends


async def get_service() -> TutorialService:
    return TutorialService()


@router.get("/progress")
async def get_progress(
    service: Annotated[TutorialService, Depends(get_service)],
) -> ProgressResponse:
    return await service.get_progress()
```

`Depends`는 Router가 전역 객체를 직접 찾지 않고 필요한 의존성을 전달받게
한다.

### lifespan

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await database.start()
    try:
        yield
    finally:
        await database.stop()
```

서버 시작과 종료 시 Service의 수명주기를 관리한다. AutoForge에서는 Service
명세가 추가된 뒤 Application 조립 코드로 생성할 예정이다.

### TestClient

```python
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

실제 네트워크 Port를 열지 않고 Endpoint를 테스트한다.

## 16. AutoForge에서 사용하는 Python 문법

### Protocol

```python
class Generator[SpecificationT](Protocol):
    def render(
        self,
        specification: SpecificationT,
    ) -> Mapping[PurePosixPath, str]:
        ...
```

명시적 상속 없이 필요한 메서드 구조를 만족하면 Generator로 사용할 수 있다.

### Python 3.12 제네릭

```python
Generator[ProjectSpec]
Generator[ModuleSpec]
```

Project와 Module Generator가 같은 계약을 사용하면서 입력 타입을 구분한다.

### StrEnum

```python
class FileOwnership(StrEnum):
    GENERATED = "generated"
    SCAFFOLDED = "scaffolded"
    USER_OWNED = "user_owned"
```

허용된 문자열 값만 사용하게 한다.

### dataclass

```python
@dataclass(frozen=True, slots=True)
class Workspace:
    root: Path
```

`frozen=True`는 생성 후 root 변경을 막고 `slots=True`는 허용하지 않은 속성의
추가를 막는다.

### Pydantic Validator

```python
@field_validator("relative_path", mode="before")
@classmethod
def validate_relative_path(cls, value: object) -> PurePosixPath:
    return validate_workspace_relative_path(value)
```

모델이 값을 저장하기 전에 경로 안전성을 검사한다.

### model_copy

```python
resolved = planned_file.model_copy(
    update={"action": PlannedAction.KEEP}
)
```

원본 모델을 변경하지 않고 새 모델을 만든다.

### pathlib

```python
target = workspace.resolve(PurePosixPath("src/game_server/main.py"))
```

문자열 결합 대신 명시적인 경로 객체를 사용한다.

### SHA-256

```python
digest = hashlib.sha256(content).hexdigest()
```

명세와 파일 내용의 변경 여부를 결정적으로 비교한다.

## 17. 설정과 의존성 주입

설정 파일은 명시적으로 로드한다.

```python
manager = ConfigManager.from_file("autoforge.yaml")
```

테스트나 Application에서는 검증된 Settings를 주입할 수 있다.

```python
settings = Settings.model_validate(data)
manager = ConfigManager(settings)
```

모듈 import 시 현재 디렉터리의 설정 파일을 자동으로 읽는 전역 Config는
사용하지 않는다.

Secret, Password와 Token은 설정 파일이나 Specification에 저장하지 않는다.
향후 Secret Provider를 통해 주입한다.

## 18. 실행과 검증

Conda 환경:

```powershell
conda activate autoforge
```

패키지 설치:

```powershell
python -m pip install -e .
```

CLI:

```powershell
autoforge --help
autoforge version
python -m autoforge.main version
```

테스트:

```powershell
pytest
python -m ruff check src tests
python -m ruff format --check src tests
```

현재 `generate`와 `plugin` 명령은 미구현 성공을 가장하지 않고 종료 코드
1과 함께 다음 구현 시점을 안내한다.

## 19. 현재 구현 상태

구현 완료:

- Registry
- PluginManager의 Registry 사용
- Event와 비동기 EventBus 기반
- Task와 TaskManager 기반
- ProjectSpec과 ModuleSpec
- 공통 Type System
- 이름, HTTP 경로와 버전 검증
- GenerationPlan과 GenerationManifest 모델
- 명세와 Content Hash
- Workspace 경로 안전 경계
- 제네릭 Generator Protocol
- 최소 FastAPI Project 메모리 렌더링
- Dry-run GenerationPlan
- Workspace 상태 기반 KEEP/SKIP/CONFLICT 판정
- GenerationPlan의 안전한 Workspace 적용
- CREATE, KEEP, SKIP 결과의 메모리 Manifest 생성
- Manifest의 결정적 JSON 저장과 검증된 로딩
- 비동기 외부 프로세스 실행과 Timeout 처리
- 생성 FastAPI 프로젝트의 실제 Import와 pytest 검증
- 공통 FieldType의 Python/Pydantic Type 변환
- ModuleSpec 기반 Pydantic Model과 Request/Response Schema 생성
- ModuleSpec 기반 FastAPI Router와 비동기 Handler Scaffold 생성
- 동일 명세 재실행 시 사용자 Handler 보존
- Manifest 기반 GENERATED 파일 안전 교체
- Endpoint 추가 시 Router 갱신과 Handler 보존
- Application Module Registry 생성
- Project와 Tutorial Module 조합 및 실제 Endpoint 호출 검증
- GenerationJob과 Project/Module Unit 집계 계약
- 복수 Manifest의 Job ID, Specification과 파일 경로 검증
- 명시적인 Config 주입
- 프로젝트 밖에서 동작하는 version CLI
- Generator 및 Validator Plugin Registry
- Built-in Generator/Validator Plugin Catalog

부분 구현:

- CLI
- Plugin Framework
- Pipeline
- Manifest
- Workspace

구현 예정:

- Tutorial Module Generator
- Application Module Registry
- Database와 Repository Plugin
- Git 자동화
- Webhook
- CI/CD
- AI 명세 및 코드 작성 보조

## 20. 개발 안전 규칙

- 수정 전 `AGENTS.md`와 필수 문서를 읽는다.
- 변경 파일과 목적을 먼저 제시한다.
- 작은 목적 단위로 구현한다.
- 공개 API를 조용히 변경하지 않는다.
- 모든 출력 경로를 Workspace 내부로 제한한다.
- SCAFFOLDED와 USER_OWNED 파일을 덮어쓰지 않는다.
- 검증 실패 결과를 Commit하거나 Push하지 않는다.
- Generator에서 Git을 직접 호출하지 않는다.
- Webhook 요청 안에서 Build와 Git 작업을 직접 실행하지 않는다.
- 비밀정보를 파일, 로그와 명령 인자에 노출하지 않는다.
- 현재 단계보다 앞선 기능을 임의로 구현하지 않는다.

## 21. 사람과 AI의 작업 시작 체크리스트

1. `AGENTS.md`를 읽는다.
2. `.codex/bootstrap.md`의 순서를 따른다.
3. 이 문서의 기준일과 Git 최근 Commit을 비교한다.
4. `.codex/current_status.md`를 읽는다.
5. `.codex/next_task.md`의 범위를 확인한다.
6. `git status --short`로 사용자 변경을 확인한다.
7. `pytest`로 기준선을 확인한다.
8. `ruff check`와 `ruff format --check`를 실행한다.
9. 참고 프로젝트의 실제 파일을 확인하지 않은 내용을 사실처럼 말하지 않는다.
10. 구현 완료와 설계 예정 상태를 구분한다.
11. 변경 후 집중 테스트와 전체 테스트를 모두 실행한다.
12. 사용자 요청 없이는 Commit과 Push를 하지 않는다.

## 22. 다음 구현 순서

현재 다음 작업은 다음과 같다.

```text
ProjectSpec.application.modules
  → 버전이 있는 GenerationJobManifest JSON
  → 기존 GenerationManifest 로딩 호환
  → 문서 종류와 format_version 판별
  → 손상 및 알 수 없는 버전 거부
```

위 수직 기능과 Tutorial Module의 Model, Schema, Router, Handler Scaffold,
Application Registry 및 사용자 코드 보존 시나리오는 구현과 테스트가
완료됐다. 생성 프로젝트의 lint와 Package Build Validator도 구현됐다.
작업별 격리 Workspace 생성과 수명주기도 구현됐다. Built-in Generator와
Validator Registry를 하나의 명시적 Catalog로 조합해 Application 계층에서
주입받을 수 있게 하는 작업도 완료됐다. 다음 단계는 Plugin Framework의
구현·문서 일치 여부를 점검한 뒤 DatabaseSpec과 Repository 계약의 최소
경계를 설계하는 것이다.

PluginLoader, Git, Webhook과 CI/CD는 위 수직 기능이 실제로 통과한 뒤
구현한다.

## 23. 관련 문서

- `README.md`
- `.codex/project_context.md`
- `.codex/architecture.md`
- `.codex/current_status.md`
- `.codex/roadmap.md`
- `.codex/next_task.md`
- `docs/architecture/system_design.md`
- `docs/architecture/generation_contract.md`
- `docs/architecture/specification_design.md`
- `docs/architecture/plugin_system.md`
- `docs/architecture/event_driven_architecture.md`

이 문서와 실제 코드가 충돌하면 테스트와 현재 코드를 사실 기준으로 삼고,
문서 불일치를 같은 변경 단위에서 수정한다.
