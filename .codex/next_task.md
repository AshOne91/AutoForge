# 다음 작업

전체 배경과 현재 구조는 `docs/PROJECT_GUIDE_2026-07-29.md`와
`docs/architecture/event_driven_architecture.md`를 먼저 읽는다.

## 완료된 기반

- Store별 Alembic Global/Shard migration
- KIS Account/Profile shard 저장과 API 2대 교차 검증
- Redis Cluster 3 Primary + 3 Replica와 primary 장애 전환
- RabbitMQ transport, Transactional Outbox Relay와 Processed Message Inbox
- KIS Profile event의 broker 장애 복구와 중복 전달 안전성 검증

## 현재 목표: Event와 Pipeline 실행 계층

EventBus는 프로세스 내부의 generic 비동기 전달만 담당하며 Git, Generator,
Plugin 또는 Pipeline 업무 규칙을 알지 않는다. RabbitMQ는 프로세스 외부 durable
transport이며 EventBus를 대체하지 않는다.

다음 구현 순서는 다음과 같다.

1. Generation Job lifecycle event와 실패 event 계약을 정의한다.
2. Pipeline이 task 순서, timeout, retry와 실패 정책을 조정하도록 구현한다.
3. Handler가 다음 event를 발행하되 EventBus에 업무 분기를 넣지 않는다.
4. audit/logging handler와 결정적 테스트를 추가한다.
5. KIS와 AutoForge 양쪽에서 실제 실행 수직 슬라이스를 검증한다.

## 후속 목표

1. 영속 Job 상태와 idempotent trigger/status API
2. Airflow 기반 News 수집/RAG 적재 workflow
3. Git checkout/branch/검증/commit/push/PR plugin
4. GitHub Webhook 서명 검증과 delivery 중복 방지
5. GitHub Actions, Docker build와 AWS 배포 계약
6. RabbitMQ HA, AWS Redis/DB Multi-AZ와 전체 장애·보안 검증

빈 미래 디렉터리를 미리 만들지 않는다. 각 단계에 진입할 때 구현 파일과 테스트를
함께 생성하고, KIS 실제 사용 사례로 계약을 검증한다.
