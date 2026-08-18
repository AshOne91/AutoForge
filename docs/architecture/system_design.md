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

## 기본 실행 흐름

```text
CLI / Control Plane / Webhook Adapter
  → ProjectSpec 로딩 및 검증
  → GenerationJob 생성
  → 격리된 Workspace 준비
  → 생성 계획 작성
  → 파일 생성
  → GenerationManifest와 GenerationJobManifest 작성
  → 생성 프로젝트 검증
  → 선택적 Commit → Push → Pull Request
```

Core 명세와 생성 계약은 GitHub, Webhook, Redis, Database, RabbitMQ 같은
구체 인프라에 의존하지 않는다. 외부 입출력은 Adapter와 Composition Root가
주입하며, 생성 대상에 필요한 Runtime Service는 ProjectSpec으로 선언한다.

### Runtime Service 조합

`tooling.local_environment`가 선택되면 AutoForge는
`environment/service-composition.json`도 생성한다. 이 파일은 같은 생성 실행에서
만든 Compose의 서비스 이름, 설정 환경 변수 이름, 수명주기, 재시작 정책, healthcheck,
의존 조건과 명세의 Redis/RabbitMQ·Durable Job 계약을 읽기 전용으로 요약한다. 이는
두 번째 명세가 아니다. `autoforge.yaml`과 생성된 Compose가 정본이며, manifest는
배포·검증 도구와 운영자가 그 결과를 기계적으로 읽기 위한 파생 산출물이다.

`tooling.local_environment`가 선택되면 AutoForge는
`environment/service-composition.json`도 생성한다. 이 파일은 같은 생성 실행에서
만든 Compose의 서비스 이름, 설정 환경 변수 이름, 수명주기, 재시작 정책, healthcheck,
의존 조건과 명세의 Redis/RabbitMQ·Durable Job 계약을 읽기 전용으로 요약한다. 이는
두 번째 명세가 아니다. `autoforge.yaml`과 생성된 Compose가 정본이며, manifest는
배포·검증 도구와 운영자가 그 결과를 기계적으로 읽기 위한 파생 산출물이다.

생성 프로젝트의 Service는 단순 라이브러리 호출이 아니라, 선택적으로 배포·확장·관측할 수 있는 Runtime 경계다. 각 Service는 자신의 설정, 수명주기, 상태 확인과 통신 계약을 소유하고, Application Composition Root 또는 명시적인 Event/Queue 계약으로 다른 Service와 조합된다. 모든 프로젝트에 모든 Service를 포함하지 않으며, ProjectSpec이 필요한 Service만 선택한다.

예를 들어 수집, canonical 저장, 임베딩, keyword/vector 검색, RAG 응답은 서로 다른 Service가 될 수 있다. AutoForge는 이들의 공통 배포·설정·소유권 골격을 생성하고, 소비자 프로젝트는 선택한 Service를 실제 도메인 흐름으로 조합한다. 현재 구현된 Service와 향후 확장 순서는 [current_status.md](../../.codex/current_status.md)와 [roadmap.md](../../.codex/roadmap.md)가 소유한다.

## 핵심 개념

### ProjectSpec

생성할 서버를 설명하는 검증 및 버전 관리 가능한 명세다. 프로젝트 정보, 패키지 이름, Framework 옵션, 모듈, 선택적 Infrastructure 설정을 포함한다.

### GenerationJob

ProjectSpec을 한 번 적용하는 작업이다. 작업 ID, 입력 출처, 상태, Workspace,
시각 정보와 구조화된 결과를 가진다. 요청 Adapter는 GenerationJob을 접수하고
실제 생성과 검증은 요청 처리 밖의 Worker가 수행한다.

GenerationJob 계약은 Project와 Module을 `GenerationUnit`으로 구분한다.
각 Unit은 기존 GenerationManifest를 그대로 보존하며 상위
GenerationJobManifest가 Job ID, Unit ID, Specification 버전·Hash와 전체
파일 경로 중복을 검증한다. Application Pipeline과 Worker가 실행 조정과
상태 전이를 담당한다.

### Workspace

작업이 파일을 생성하거나 수정할 수 있는 유일한 영역이다. 경로 이탈을 방지하고 동시 작업을 격리한다.

### 생성 계획과 파일 Manifest

생성 계획은 실제 쓰기 전 디렉터리와 파일의 미리보기다. Dry-run은 계획만
반환한다. Manifest는 각 파일의 소유권, 내용 Hash와 적용 상태를 기록한다.
세부 필드와 반복 생성 규칙은 `generation_contract.md`가 소유한다.

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

## Git 자동화 경계

```text
GitHub 이벤트
  → 인증 및 중복 제거
  → GenerationJob
  → 격리된 저장소 Checkout
  → 생성 및 검증
  → 작업 브랜치
  → Commit → Push → Pull Request
```

Webhook은 작업 접수 후 응답하며 기본 브랜치에 직접 Push하지 않는다. 구체
상태 전이와 Provider 계약은 `git_automation.md`가 소유한다.

## Plugin 전략

Plugin은 Generator와 Validator 같은 확장 구현을 등록하는 단위다. Registry가
등록 상태를 소유하고 PluginManager와 PluginLoader가 수명주기와 발견·검증을
담당한다. Plugin은 선언된 Capability와 권한 범위를 벗어나지 않으며 구체
계약은 `plugin_system.md`가 소유한다.

## EventBus와 Pipeline

EventBus는 Generic Event의 구독, 구독 해제와 비동기 전달만 담당하며 업무
순서를 실행하지 않는다. Pipeline은 하나의 Job 안에서 Task 순서와 실패 정책을
소유한다. Handler는 상태 변화와 관찰 기능을 연결하되 등록 순서로 Workflow를
숨기지 않는다. 상세 계약은 `event_driven_architecture.md`가 소유한다.

## 상세 문서

- `generation_contract.md`: 파일 소유권, 반복 생성, Manifest, 검증 계약
- `specification_design.md`: Project, Application, Module, API, Model, DB 명세
- `database_generation.md`: DB 명세, 생성물, Runtime 경계
- `event_driven_architecture.md`: EventBus, Handler, Pipeline과 Transport 경계
- `plugin_system.md`: Registry, PluginManager, PluginLoader 계약
- `git_automation.md`: Git Provider와 Delivery 상태 전이
- `control_plane_persistence.md`: Job 저장·임대·복구 계약
- 나머지 인프라 정본은 각 `*_contract.md`, `*_policy.md`와 서비스별 문서가 소유한다.
