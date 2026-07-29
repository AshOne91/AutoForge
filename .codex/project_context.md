# AutoForge 프로젝트 배경

## 제품 목표

AutoForge는 검증된 프로젝트 명세를 바탕으로 모듈형 FastAPI 웹서버 프로젝트를 생성하는 Python 자동화 플랫폼이다.

1. 로컬 실행: CLI → 프로젝트 명세 → 코드 생성 → 검증
2. 자동 실행: Git 이벤트 → Webhook → 작업 생성 → 코드 생성 → 검증 → Git 반영

첫 번째 MVP는 로컬 실행 방식이다. Webhook과 Git 자동화는 로컬 생성과 검증이 안정된 이후 구현한다.

## 참고 프로젝트

- `common-tool`: 명령과 설정 기반 코드 생성 방식을 참고한다. AutoForge는 포팅이 아니라 재설계 프로젝트다.
- `gameserver`: Application, 도메인 Template, Service, Tool의 책임 분리를 참고한다.
- `base_server`: 생성될 FastAPI 애플리케이션의 Router, Domain, Service, 설정, 테스트, 컨테이너 구조를 참고한다.

도메인 Template과 코드 렌더링 템플릿은 다른 개념으로 구분한다. 프로젝트 전용 금융, 채팅, AI 기능이나 전역 ServiceContainer 패턴은 그대로 복사하지 않는다.

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