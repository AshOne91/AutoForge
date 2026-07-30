# AutoForge 아키텍처

## 기본 실행 흐름

```text
ProjectSpec
  → 프로젝트 명세 검증
  → GenerationJob
  → 격리된 Workspace
  → 생성 계획
  → Generator
  → 파일 Manifest
  → 검증 Pipeline
  → 실행 결과
```

검증에 성공한 결과만 작업 브랜치, Commit, Push, Pull Request 단계로 진행할 수 있다.

## 진입점

- CLI: 첫 번째 MVP의 기본 진입점
- Webhook: Git 이벤트를 인증하고 작업을 생성하는 후속 어댑터

Webhook의 HTTP 요청 안에서 코드 생성, 빌드, Commit을 직접 실행하지 않는다.

## 계층

- CLI: 명령 입력과 결과 표시
- Application: 작업과 Pipeline 실행 조정
- Core: 명세, 작업 모델, Generator 계약, 결과, Task, Event, 정책
- Services: 생성, 검증, Workspace, Build 및 후속 Git 유스케이스
- Infrastructure: 파일시스템, 외부 프로세스, Git 공급자, 렌더링, Webhook 어댑터

## 책임 경계

- Generator는 Git에 접근하지 않는다.
- Git 서비스는 생성 규칙을 알지 못한다.
- 모든 출력은 Workspace 내부에만 생성한다.
- Manifest는 생성, 변경, 동일, 건너뜀, 충돌 파일을 기록한다.
- 검증 실패 시 Git 반영을 금지한다.
- EventBus는 주요 컴포넌트의 중앙 통신 수단이며 업무 로직은 가지지 않는다.
- Handler는 Event를 Application 동작에 연결하고 결과 Event를 발행한다.
- Pipeline은 Job 내부 Task 실행 순서와 실패·재시도·Timeout 정책을 제어한다.
- Handler 등록 순서나 Event 연쇄만으로 Pipeline 순서를 표현하지 않는다.
- Plugin은 검증된 생성 기능을 확장하며 첫 Generator의 필수 요소가 아니다.
