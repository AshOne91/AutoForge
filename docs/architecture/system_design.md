# AutoForge 시스템 설계

## 목적

AutoForge는 선언형 ProjectSpec을 바탕으로 모듈형 FastAPI 웹서버 프로젝트를 생성한다. 생성 프로젝트를 로컬에서 검증하고, 이후 동일한 과정을 GitHub 이벤트로 실행해 검증된 변경을 Pull Request로 전달한다.

AutoForge는 생성 및 자동화 도구이고 생성된 FastAPI 프로젝트는 별도의 결과물이다.

AutoForge의 최종 구조는 세 축을 함께 유지한다.

```text
반복 코드 생성
  + Plugin, Metadata, EventBus, Pipeline 기반 확장
  + Git 이벤트 및 CI/CD 자동화
```

## 참고 아키텍처

- `common-tool`: 명령 중심 생성 과정과 설정 기반 모델
- `gameserver`: Application, Domain, Service, Tool 책임 분리
- `base_server`: FastAPI Application, Router, Domain, Service, 설정, 테스트, Docker 구조

참고 프로젝트를 복사하지 않고 유용한 책임 경계만 유지한다.

참고 프로젝트의 역할, 채택·교체·폐기 기준과 두 저장소의 책임은
`reference_project_strategy.md`를 따른다. SKN12 `base_server`는 AutoForge가
있었다면 생성·조립했을 실제 서비스의 롤모델로 사용한다.

`common-tool`이 생성하던 Application, Template, Packet, Protocol, DB 및
Controller의 반복 코드는 AutoForge의 Project, Module, Schema, Router,
Repository Generator로 재설계한다.

## 로컬 MVP 흐름

```text
CLI
  → ProjectSpec 로딩 및 검증
  → GenerationJob 생성
  → 격리된 Workspace 준비
  → 생성 계획 작성
  → 파일 생성
  → 파일 Manifest 작성
  → 생성 프로젝트 검증
  → 성공 또는 실패 결과 보고
```

AutoForge Core와 명세 검증은 GitHub, Webhook, Redis, Database, RabbitMQ와
AI 없이 동작해야 한다. 반면 `kis-auto-trading`의 생성 Blueprint에는 관계형
Database, Redis와 RabbitMQ를 필수 Runtime Service로 포함한다.

## 생성될 기본 서버 구조

```text
generated-project/
├── src/project_name/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── routers/
│   │   ├── __init__.py
│   │   └── health.py
│   ├── domain/__init__.py
│   └── services/__init__.py
├── tests/test_health.py
├── pyproject.toml
├── README.md
└── Dockerfile
```

Dockerfile 생성 여부는 ProjectSpec으로 선택할 수 있다.

## 핵심 개념

### ProjectSpec

생성할 서버를 설명하는 검증 및 버전 관리 가능한 명세다. 프로젝트 정보, 패키지 이름, Framework 옵션, 모듈, 선택적 Infrastructure 설정을 포함한다.

### GenerationJob

ProjectSpec을 한 번 적용하는 작업이다. 작업 ID, 입력 출처, 상태, Workspace, 시각 정보, 구조화된 결과를 가진다. 향후 Webhook은 HTTP 요청 안에서 Generator를 실행하지 않고 GenerationJob을 생성한다.

현재 GenerationJob 계약은 Project와 Module을 `GenerationUnit`으로 구분한다.
각 Unit은 기존 GenerationManifest를 그대로 보존하며 상위
GenerationJobManifest가 Job ID, Unit ID, Specification 버전·Hash와 전체
파일 경로 중복을 검증한다. Job 실행 조정과 상태 전이는 후속 Service가
담당한다.

### Workspace

작업이 파일을 생성하거나 수정할 수 있는 유일한 영역이다. 경로 이탈을 방지하고 동시 작업을 격리한다.

### 생성 계획과 파일 Manifest

생성 계획은 실제 쓰기 전 디렉터리와 파일의 미리보기다. Dry-run은 계획만 반환한다. Manifest는 각 파일을 생성, 변경, 동일, 건너뜀, 충돌 상태로 기록한다.

Application Module Registry는 ProjectSpec에 선언된 Module Router를 생성 코드로
연결한다. `application/generated/module_registry.py`가 Router 튜플을 제공하고
Application Factory가 Health Router 이후 선언 순서대로 등록한다.

### Generator

검증된 ProjectSpec을 생성 계획으로 변환하고 Workspace에 적용한다. Commit, Push, Pull Request, Webhook을 처리하지 않는다.

### 검증 Pipeline

Import, pytest, lint, 패키지·빌드 검사를 순서대로 실행한다. 실패 시 모든 Git 반영을 차단한다.

## 생성 안전 정책

- 모든 출력 경로를 Workspace 하위로 제한한다.
- 잘못된 프로젝트·패키지·모듈 이름은 쓰기 전에 거부한다.
- 사용자 관리 파일을 조용히 덮어쓰지 않는다.
- 생성 파일과 수동 관리 파일을 구분한다.
- 실제 변경 전 Dry-run을 지원한다.
- 같은 명세의 반복 생성 결과가 결정적이어야 한다.
- 부분 실패를 명확히 보고한다.
- 비밀정보를 파일이나 명령 인자로 노출하지 않는다.
- 외부 프로세스에 제한 시간을 적용한다.

## 향후 Git 자동화

```text
GitHub 이벤트
  → 인증 및 중복 제거
  → GenerationJob
  → 격리된 저장소 Checkout
  → 생성 및 검증
  → 작업 브랜치
  → Commit → Push → Pull Request
```

Webhook은 작업 접수 후 응답하며 기본 브랜치에 직접 Push하지 않는다.

## Plugin 전략

첫 FastAPI Generator는 일반 구현으로 작성한다. 실제 확장 지점이 확인된 이후 Project Blueprint, 모듈 Generator, 선택적 Service, 검증 작업을 Plugin으로 제공한다. Plugin은 Git에 직접 접근할 수 없고 PluginLoader는 계약 검증 이후 구현한다.

Plugin은 최종 아키텍처의 핵심 확장 단위다. Generator, Validator, Builder,
Git Provider, CI/CD, Deployment 기능을 Plugin으로 확장할 수 있다.

Plugin Metadata는 ID, 버전, API 버전, 유형, Capability, 의존성, 지원 명세
버전, 권한을 선언한다.

## EventBus와 Pipeline

EventBus는 AutoForge 주요 컴포넌트 사이의 중앙 통신 메커니즘이다. Webhook,
Pipeline, Task, Plugin, Generator, Git과 Notification의 주요 상태 변화는
Event로 표현한다. EventBus 자체는 이 컴포넌트의 내부 구조나 업무 규칙을
알지 않으며 Generic Event의 구독, 구독 해제와 비동기 전달만 담당한다.

Pipeline은 하나의 Job 안에서 Task의 실행 순서와 실패·재시도·Timeout 정책을
제어한다.

```text
ValidateSpec
→ ResolvePlugins
→ PrepareWorkspace
→ PlanGeneration
→ Generate
→ Validate
→ Test
→ Build
→ Delivery
```

Handler는 Event를 Application Service 동작에 연결하고 처리 결과를 다시
Event로 발행한다. Logging, Audit, Metrics와 상태 추적도 Handler로 연결한다.
Handler 등록 순서나 Event 연쇄만으로 Pipeline 순서를 숨기지 않는다.
EventBus는 중앙 통신 수단이지만 중앙 업무 실행기는 아니다.

Command는 실행 요청이고 Event는 이미 발생한 사실이다. 현재 EventBus는
Event만 다루며 Command 전달 API는 첫 GenerationPipeline 구현 전에 별도로
결정한다.

상세 결정은 `event_driven_architecture.md`를 따른다.

## 상세 문서

- `generation_contract.md`: 파일 소유권, 반복 생성, Manifest, 검증 계약
- `specification_design.md`: Project, Application, Module, API, Model, DB 명세
- `event_driven_architecture.md`: EventBus, Handler, Pipeline과 Transport 경계

## 첫 번째 MVP 제외 범위

- `base_server`의 모든 기능 재현
- 금융, 채팅, AI 전용 Domain
- Database 자동 구축
- GitHub Webhook과 Git 자동화
- 분산 작업 실행
- AI가 작성한 운영 코드
