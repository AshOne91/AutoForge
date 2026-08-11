# base_server 수준의 생성 Blueprint 전략

> **문서 역할: REFERENCE**
> 이 문서는 `base_server`에서 추출한 목표와 현대화 원칙을 보존한다. 현재 구현
> 상태, Roadmap 또는 다음 작업의 정본이 아니다. 현재 계약은
> [`system_design.md`](../architecture/system_design.md), 구현 상태와 계획은
> [`.codex/current_status.md`](../../.codex/current_status.md),
> [`.codex/roadmap.md`](../../.codex/roadmap.md),
> [`.codex/next_task.md`](../../.codex/next_task.md)를 따른다.

## 목적

AutoForge의 목표는 `base_server`를 그대로 복제하거나 AutoForge 자신을 웹서비스로
바꾸는 것이 아니다. 하나의 검증 가능한 명세에서 `base_server`급 FastAPI 서버의 공통
구조를 반복 생성하고, 개발자는 생성 경계 밖의 도메인 업무만 구현하게 만드는 것이다.

`kis-auto-trading`은 이 목표를 검증하는 첫 번째 소비자다.

```text
Project/Application/Module 명세
  -> FastAPI 프로젝트와 Module 조합
  -> DB, Redis, Queue, Worker, Scheduler, observability 산출물
  -> Docker/Compose/Kubernetes 실행 산출물
  -> 검증, Git automation, 배포 자동화
```

## 역할 분리

| 대상 | 책임 |
| --- | --- |
| `base_server` | 수작업으로 구현된 기능·운영 구조의 참조 모델 |
| AutoForge | 명세, 생성, ownership, 검증, Git automation 플랫폼 |
| `kis-auto-trading` | 생성된 구조가 실제 제품 요구에서 유효한지 검증하는 소비자 |

따라서 `base_server`의 개별 Router나 전역 ServiceContainer를 복사하지 않는다. 그
프로젝트가 보여 주는 중요한 원리는 Application이 필요한 Module과 Service를 선택해
조합하는 Composition Root라는 점이다.

## base_server에서 계승할 범위

`base_server`는 FastAPI Router, Global/Sharded database, Redis session/cache,
Queue/Outbox, scheduler, distributed lock, WebSocket, 외부 API, 파일 로그,
환경별 설정, Docker 역할 분리를 한 Application에 조합한다.

AutoForge는 이를 다음처럼 현대화한다.

| 참조 구현 | AutoForge 방향 |
| --- | --- |
| 정적 ServiceContainer와 전역 상태 | lifespan과 명시적 dependency provider |
| 수작업 Template/Router 조립 | 결정적 Module/Application generation |
| JSON 설정과 수동 SQL | 검증 가능한 Spec, DDL, Alembic, Manifest |
| 특정 MySQL/AWS 구현 결합 | provider/adapter 경계와 소비자 선택 |
| 단일 서버 초기화 흐름 | app, worker, scheduler 역할별 실행 산출물 |
| 수동 Compose/Kubernetes | 선택형 generator와 재현 가능한 검증 |

## 금지 사항

- `base_server`의 전역 singleton과 거대한 startup 흐름을 복제하지 않는다.
- 13개 Router를 한 번에 generator 기능으로 만들지 않는다.
- 실제 소비자가 없는 cloud, broker, database provider를 먼저 추가하지 않는다.
- 사용자 소유 KIS 전략·뉴스 수집·주문 업무를 AutoForge generator에 넣지 않는다.
