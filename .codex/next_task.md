# 다음 작업

전체 배경과 현재 구조는 `docs/PROJECT_GUIDE_2026-07-29.md`를 먼저 읽는다.

## 현재 목표

DatabaseSpec과 Repository 최소 명세 계약은 구현되었고
`C:\kis-auto-trading\specifications\account.yaml`로 검증되었다.

기술 중립 Repository Protocol과 테스트용 Fake Repository Generator는
구현되었고 kis-auto-trading Account/Profile 명세로 렌더링을 검증했다.

PostgreSQL DDL Generator로 로그인 Global DB와 개인정보 Shard DB의 분리된 SQL을
생성하고 kis-auto-trading 명세로 검증했다. SQLAlchemy async Model Generator,
request-scoped Session, ShardRouter Protocol, Repository Adapter와 Domain/Record
변환 Generator를 구현했다. 여러 Project/Module 결과를 조립해 Manifest와 함께
대상 저장소에 적용하는 Generation Runner와 CLI도 구현하여 kis-auto-trading에
실제 생성 결과를 적용했다.

Redis Service Blueprint의 standalone과 Sentinel 연결 공급자를 구현했고,
kis-auto-trading에서 Primary 중지, Replica 자동 승격, 기존 session 읽기와 신규
session 쓰기를 실제 Docker 토폴로지로 검증했다. Cluster-aware 연결과 AWS managed
환경 계약은 Redis 후속 범위로 유지한다.

다음 목표는 Alembic 실행 환경을 생성하여 저장된 Global/Shard SQL의 적용 순서와
상태를 관리하는 것이다.

Repository와 DB 기반 이후 Redis Service와 RabbitMQ Transport를 필수 서비스로
구현한다. Redis는 cache/coordination, RabbitMQ는 Queue/Worker 책임을 가지며
두 책임을 하나의 Service로 합치지 않는다.

## 근거 문서

- `docs/architecture/generation_contract.md`
- `docs/architecture/specification_design.md`
- `docs/architecture/system_design.md`

## 다음 구현 범위

1. Alembic 실행 환경의 GENERATED/SCAFFOLDED 파일 소유권 확정
2. Global DB와 모든 Shard DB에 동일 순서로 migration을 적용하는 계약 정의
3. 기존 PostgreSQL DDL 산출물과 Alembic revision의 중복 책임 방지
4. 반복 생성, migration 상태, 실패 시 중단 정책 확정
5. kis-auto-trading 격리 Workspace에서 생성·import·pytest 검증
6. 구현 전 구체적인 코드·테스트 파일 계획 제시

## 이번 범위에서 구현하지 않음

- 추가 DB Provider
- 로그인 업무 Handler와 인증 정책
- Redis Sentinel/Cluster 구현
- RabbitMQ와 Outbox
- 권한의 OS 수준 Sandbox 강제
- Webhook
- Git Commit, Push, Pull Request
- CI/CD 실행
- Database Generator
- AI 생성

## 유지할 최종 아키텍처

- Plugin은 Generator, Validator, Builder, Git, CI/CD 기능을 확장한다.
- Plugin Metadata는 호환성, Capability, 의존성, 권한을 표현한다.
- EventBus는 실행 사건을 전달한다.
- Pipeline은 실행 순서와 실패 정책을 제어한다.
- Manifest는 생성 파일의 소유권과 출처를 추적한다.

구체적인 코드 파일과 테스트 계획을 먼저 제시하고 사용자 승인을 받은 후에만 구현한다.

현재 비어 있는 미래 기능 디렉터리는 제거된 상태다. Plugin, Database, Git,
Webhook 단계에 진입할 때 `.codex/roadmap.md`의 해당 체크 항목에 따라 소스와
테스트 디렉터리를 구현 파일과 함께 다시 생성한다.
