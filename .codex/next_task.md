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

Store별 Alembic 실행 환경과 최초 baseline revision 생성을 완료했다. 생성된
`scripts/migrate.py`가 identity DB와 account shard DB 2개에 각 store의 revision을
적용하고, 각 `alembic_version` 값을 기록하는 것을 실제 Docker 환경에서 검증했다.

Bearer current_session 의존성 생성과 kis-auto-trading Account/Profile의 실제 account
shard 저장을 완료했다. API 2가 저장한 Profile을 API 1이 조회하고, 세션에서 선택된
shard에만 행이 존재하며 반대 shard에는 저장되지 않는 것을 Docker 환경에서 검증했다.

다음 목표는 Redis Cluster 3 Primary + 3 Replica 연결 공급자와 통합 토폴로지를
추가하되, 기존 SessionStore 업무 계약과 Handler 코드는 변경하지 않는 것이다.

Repository와 DB 기반 이후 Redis Service와 RabbitMQ Transport를 필수 서비스로
구현한다. Redis는 cache/coordination, RabbitMQ는 Queue/Worker 책임을 가지며
두 책임을 하나의 Service로 합치지 않는다.

## 근거 문서

- `docs/architecture/generation_contract.md`
- `docs/architecture/specification_design.md`
- `docs/architecture/system_design.md`

## 다음 구현 범위

1. redis-py Cluster async client와 현재 SessionStore adapter 호환성 확인
2. Cluster endpoint 설정 명세와 standalone/sentinel/cluster 배타 검증
3. Session key와 user-session set이 같은 slot을 쓰는 hash-tag 규칙 확정
4. Redis Cluster 3 Primary + 3 Replica Compose 토폴로지 구성
5. API 2대 세션 읽기·쓰기와 primary 장애 후 복구 검증
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
