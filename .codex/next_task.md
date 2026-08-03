# 다음 작업

전체 배경과 현재 구조는 `docs/PROJECT_GUIDE_2026-07-29.md`와
`docs/architecture/event_driven_architecture.md`를 먼저 읽는다.

## 완료된 기반

- Store별 Alembic Global/Shard migration
- KIS Account/Profile shard 저장과 API 2대 교차 검증
- Redis Cluster 3 Primary + 3 Replica와 primary 장애 전환
- RabbitMQ transport, Transactional Outbox Relay와 Processed Message Inbox
- KIS Profile event의 broker 장애 복구와 중복 전달 안전성 검증

## 완료: Event와 Pipeline 실행 계층

EventBus는 프로세스 내부의 generic 비동기 전달만 담당하며 Git, Generator,
Plugin 또는 Pipeline 업무 규칙을 알지 않는다. RabbitMQ는 프로세스 외부 durable
transport이며 EventBus를 대체하지 않는다.

완료된 구현은 다음과 같다.

1. Generation Job lifecycle event와 실패 event 계약
2. 명시적 task 순서, timeout, retry, 실패와 cancellation 정책
3. Prepare → Generate → Validate Application Pipeline
4. JobStore 선저장 후 lifecycle event 발행
5. import, pytest, Ruff와 wheel build 성공 조건

## 현재 목표: 관찰과 영속 Job 실행

1. 구조화된 logging handler를 추가한다.
2. append-only audit record 계약과 adapter를 추가한다.
3. PostgreSQL JobStore와 optimistic concurrency를 구현한다.
4. idempotency key 기반 trigger/status Application API를 구현한다.
5. KIS에서 새 Generation Pipeline 전체를 실제 실행해 검증한다.

## 후속 목표

1. Airflow 기반 News 수집/RAG 적재 workflow
2. Git checkout/branch/검증/commit/push/PR plugin
3. GitHub Webhook 서명 검증과 delivery 중복 방지
4. GitHub Actions, Docker build와 AWS 배포 계약
5. RabbitMQ HA, AWS Redis/DB Multi-AZ와 전체 장애·보안 검증

빈 미래 디렉터리를 미리 만들지 않는다. 각 단계에 진입할 때 구현 파일과 테스트를
함께 생성하고, KIS 실제 사용 사례로 계약을 검증한다.
