# AutoForge 프로젝트 배경

## 제품 목표

AutoForge는 검증된 프로젝트 명세를 바탕으로 모듈형 FastAPI 웹서버 프로젝트를 생성하는 Python 자동화 플랫폼이다.

2026-07-30 최종 갱신 기준 전체 구조, 설계 이유, 구현 상태와 FastAPI 문법은
`docs/PROJECT_GUIDE_2026-07-29.md`를 기준 인수인계 문서로 사용한다.

1. 로컬 실행: CLI → 프로젝트 명세 → 코드 생성 → 검증
2. 자동 실행: Git 이벤트 → Webhook → 작업 생성 → 코드 생성 → 검증 → Git 반영

첫 번째 MVP는 로컬 실행 방식이다. Webhook과 Git 자동화는 로컬 생성과 검증이 안정된 이후 구현한다.

## 참고 프로젝트

- `common-tool`: 명령과 설정 기반 코드 생성 방식을 참고한다. AutoForge는 포팅이 아니라 재설계 프로젝트다.
- `gameserver`: Application, 도메인 Template, Service, Tool의 책임 분리를 참고한다.
- `base_server`: 생성될 FastAPI 애플리케이션의 Router, Domain, Service, 설정, 테스트, 컨테이너 구조를 참고한다.
- `SKN12-FINAL-2TEAM`: 실제 서비스 기능, 이벤트, 큐와 Kubernetes 등 수작업
  구현을 분석해 현대화할 기능 원본이다.
- `kis-auto-trading`: SKN12의 기능을 현대적인 구조로 재구성할 첫 실제 생성
  대상 프로젝트다.

도메인 Template과 코드 렌더링 템플릿은 다른 개념으로 구분한다. 프로젝트 전용 금융, 채팅, AI 기능이나 전역 ServiceContainer 패턴은 그대로 복사하지 않는다.

프로젝트 관계는 다음을 기준으로 한다.

```text
common-tool + gameserver
  → 반복 코드 생성 방식의 원형

SKN12-FINAL-2TEAM
  → 실제 기능과 수작업 인프라 구현의 원형

AutoForge
  → 반복 구조를 Specification, Generator와 Plugin으로 자동화

kis-auto-trading
  → AutoForge로 현대화해 생성할 첫 실제 서비스
```

SKN12 코드를 그대로 복사하지 않는다. 반복 구조는 Generator, 기술 구현은
Protocol과 Adapter 또는 Plugin, 프로젝트 고유 비즈니스 로직은 사용자 소유
코드로 분리한다. 실제로 확인하지 않은 SKN12 기능은 구현된 사실처럼 문서화
하지 않는다.

## 이중 저장소 개발 원칙

AutoForge와 `C:\kis-auto-trading`은 독립 Git 저장소로 유지하면서 함께 개발한다.

- AutoForge는 명세, Generator, Plugin, Manifest와 검증을 소유한다.
- kis-auto-trading은 실제 명세, 생성 결과와 거래 업무 로직을 소유한다.
- AutoForge의 범용 기능은 kis-auto-trading에 실제 적용하여 완료를 검증한다.
- kis-auto-trading의 반복 골격을 먼저 수작업으로 확장하지 않는다.
- 두 저장소의 테스트, commit과 push는 각각 분리한다.

Database 설계는 `common-tool`의 생성 범위, `game-server`의 수평 확장,
SKN12 `base_server`의 FastAPI async DB 수명주기를 참고한다. 상세 결정은
`docs/architecture/database_generation.md`를 따른다.

## 설계 원칙

- 프로젝트 명세 기반
- 안전하고 결정적인 코드 생성
- I/O 작업은 비동기 우선
- 테스트 가능하고 조합 가능한 구조
- 명시적인 의존성
- 격리된 Workspace
- 검증 성공 전 Git 작업 금지
- 핵심 Generator 검증 후 확장 기능 도입

## 첫 번째 MVP 범위

로컬 YAML 명세를 읽고 최소 FastAPI 프로젝트를 생성한 다음 생성 파일을 기록하고 결과를 검증한다.

Webhook, Git 자동화, AI, 분산 작업자, Plugin 마켓플레이스, 필수 Database·Cache 서비스는 포함하지 않는다.
