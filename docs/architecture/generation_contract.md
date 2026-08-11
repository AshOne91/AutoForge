# AutoForge 생성 계약

## 목적

이 문서는 AutoForge가 어떤 입력을 받아 어떤 파일을 생성하고, 반복 생성에서
사용자 코드를 어떻게 보호하며, 생성 결과를 어떻게 검증하는지 정의한다.

AutoForge는 일회성 프로젝트 Scaffold 도구가 아니다. 서버 개발에서 반복되는
Application 연결, API/Packet, Model, Router, Service, DB Schema, Repository,
Test, CI/CD 설정을 명세로 관리하는 생성 및 자동화 플랫폼이다.

## 생성 단위

### Project

새 저장소 또는 Python 패키지의 기본 구조를 생성한다.

- `src` 패키지 레이아웃
- `pyproject.toml`
- FastAPI Application Factory
- lifespan 기본 구조
- 설정과 로깅
- Health Router
- 테스트
- 선택적 Docker 및 CI/CD 설정

### Application

활성화된 Module과 Service를 조합한다.

- Router 등록
- Dependency Provider 등록
- Service 초기화 및 종료
- Module Metadata 등록
- Application 설정 조합

### Module

Account, Tutorial, Item처럼 하나의 도메인 기능 단위를 생성한다.

- Request/Response Schema
- Domain Model
- Router
- Handler 골격
- Service 골격
- Repository 계약
- 테스트

### Database

DB Schema 명세에서 저장 계층 코드를 생성한다.

- ORM Model
- Repository Protocol
- Persistence Adapter 골격
- Migration 또는 DDL
- 테스트용 Fake Repository

Database 생성의 Schema, Repository, Data Placement, Runtime Topology,
Transaction/Outbox 경계는 `database_generation.md`에서 정의한다.

## 생성 파일 소유권

Python에는 C#의 `partial class`가 없으므로 파일 단위로 소유권을 분리한다.

### GENERATED

명세만으로 완전히 재현할 수 있는 파일이다.

```text
modules/item/generated/schemas.py
modules/item/generated/models.py
modules/item/generated/router.py
application/generated/module_registry.py
```

- AutoForge가 반복 생성할 수 있다.
- 사용자가 직접 수정하지 않는다.
- Generator와 명세 Hash를 Metadata에 기록한다.
- 내용 Hash가 예상과 다르면 수동 변경으로 판단하고 정책에 따라 충돌시킨다.

### SCAFFOLDED

최초 한 번만 골격을 생성하고 이후 사용자 소유로 전환되는 파일이다.

```text
modules/item/handlers.py
modules/item/service.py
```

- 파일이 없을 때만 생성한다.
- 파일이 있으면 변경하지 않는다.
- 명세에 새 Handler가 추가돼도 기존 파일을 자동 덮어쓰지 않는다.
- 누락된 구현은 검증 결과 또는 별도 보조 파일로 보고한다.

### USER_OWNED

사용자가 직접 만든 파일이다.

```text
modules/item/custom/pricing.py
modules/item/custom/reward_policy.py
```

AutoForge는 생성, 변경, 삭제하지 않는다.

## 권장 Python 출력 구조

```text
src/<package_name>/
├── application/
│   ├── app_factory.py
│   ├── lifespan.py
│   └── generated/
│       └── module_registry.py
├── modules/
│   └── <module_name>/
│       ├── generated/
│       │   ├── schemas.py
│       │   ├── models.py
│       │   ├── router.py
│       │   └── metadata.json
│       ├── handlers.py
│       ├── service.py
│       └── custom/
├── services/
├── infrastructure/
└── main.py
```

`generated` 디렉터리는 기계 생성 영역이고, 그 밖의 Handler 및 Custom
디렉터리는 사용자 코드 영역이다.

## 생성 계획

Generator는 파일을 쓰기 전에 GenerationPlan을 만든다.

각 계획 항목은 다음 정보를 가진다.

- 상대 경로
- Generator ID와 버전
- 소유권
- 예정 작업
- 명세 Hash
- 예상 내용 Hash
- 교체 대상의 이전 Content Hash
- 의존 명세 또는 Module

예정 작업은 다음 중 하나다.

- CREATE
- REPLACE_GENERATED
- KEEP
- SKIP
- CONFLICT

Dry-run은 GenerationPlan만 반환하고 파일시스템을 변경하지 않는다.

## Manifest

GenerationManifest는 실제 실행 결과를 기록한다.

- 작업 ID
- ProjectSpec 버전과 Hash
- 생성 파일 목록
- 파일별 소유권
- Generator ID와 버전
- 명세 Hash와 내용 Hash
- 생성, 변경, 동일, 건너뜀, 충돌, 실패 상태

Manifest 경로는 Workspace를 기준으로 한 상대 경로만 사용한다.
GenerationJobManifest는 여러 GenerationUnit의 Manifest를 Job 단위로 묶고
Job ID, Unit ID, 명세 버전·Hash와 전체 상대 경로의 중복을 검증한다.

## 반복 생성 규칙

1. ProjectSpec과 ModuleSpec을 검증한다.
2. 현재 Manifest와 파일 Hash를 읽는다.
3. GenerationPlan을 만든다.
4. USER_OWNED 파일은 대상에서 제외한다.
5. SCAFFOLDED 파일이 이미 있으면 보존한다.
6. GENERATED 파일에 예상하지 못한 수동 변경이 있으면 충돌로 처리한다.
7. 임시 Workspace에서 새 결과를 생성한다.
8. Import, Test, Build 검증을 실행한다.
9. 검증 성공 후에만 대상에 적용한다.
10. 새 Manifest를 기록한다.

강제 덮어쓰기 옵션은 기본값이 아니며 별도 승인과 명시적 옵션이 필요하다.

`REPLACE_GENERATED`는 이전 Manifest가 같은 Generator와 source로 기록한
GENERATED 파일에만 허용한다. 현재 파일 Hash가 Manifest Content Hash와
일치해야 하며, 적용 직전에도 같은 이전 Hash를 다시 확인한다.

## 생성 과정의 Event

Generator와 Pipeline은 다음 수명주기 Event를 발행한다.

- `GenerationJobPlannedEvent`
- `GenerationStartedEvent`
- `GenerationCompletedEvent`
- `GenerationFailedEvent`
- 검증 시작·완료·실패 Event
- Git Commit·Push·Pull Request Event

Event는 상태 알림과 Logging, Audit, Metrics뿐 아니라 AutoForge 주요
컴포넌트 사이의 통신 경계에도 사용한다. EventBus는 업무 로직이나 실행
순서를 제어하지 않는다. Pipeline이 Task 순서와 실패 정책을 소유하고
Application Handler가 처리 결과를 Event로 발행한다. 상세 경계는
`event_driven_architecture.md`를 따른다.

## 검증 조건

생성 성공은 파일 쓰기 성공만 의미하지 않는다.

1. 명세 검증 성공
2. Workspace 경로 검증 성공
3. 충돌 정책 통과
4. 계획된 파일 생성 성공
5. Python Import 성공
6. 생성 프로젝트 pytest 성공
7. 선택된 Validator Plugin 성공
8. Manifest 기록 성공

검증 실패 시 Git Commit, Push, Pull Request를 실행하지 않는다.
