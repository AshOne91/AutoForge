# 참고 프로젝트 적용 전략

## 목적

AutoForge와 `kis-auto-trading`은 이미 검증된 참고 프로젝트의 구조와 문제 해결
경험을 활용한다. 참고 코드를 무조건 복사하거나 반대로 모두 새로 만들지 않는다.

이 문서는 각 프로젝트의 역할과 코드 채택 기준을 고정한다.

## 프로젝트 관계

```text
common-tool
  → 무엇을 자동 생성해야 하는지 보여주는 생성기 원형

game-server
  → 생성된 Application, Domain, Service와 DB가 어떻게 조립되는지 보여주는 실행 원형

SKN12 base_server
  → AutoForge가 있었다면 생성·조립했을 FastAPI 서비스의 롤모델

AutoForge
  → 반복 구조와 외부 서비스 연결을 명세에서 생성하고 검증하는 플랫폼

kis-auto-trading
  → AutoForge를 사용해 SKN12 기능을 현대화하는 실제 서비스
```

SKN12는 AutoForge의 소스 코드가 아니다. SKN12가 해결하려던 요구사항과 실제
동작하는 Domain 흐름을 AutoForge 명세와 Generator의 검증 사례로 사용한다.

## AutoForge의 책임

AutoForge는 다음 산출물을 명세에서 생성한다.

- Project와 Application 골격
- Domain Module 구조
- Packet/API request와 response schema
- Router와 Application Handler 골격
- Repository Protocol과 Fake Repository
- DB model과 migration
- Redis Service Adapter와 Fake
- RabbitMQ Publisher, Consumer와 Worker 골격
- Outbox relay 연결
- 외부 서비스 Adapter 골격
- lifespan과 dependency provider
- Docker, Kubernetes와 CI/CD 설정
- 생성 Manifest와 검증 결과

AutoForge는 실제 투자 판단, 주문 정책 또는 사용자별 위험 규칙을 소유하지 않는다.

## kis-auto-trading의 책임

`kis-auto-trading`은 다음을 소유한다.

- Account/Profile, Portfolio, Order와 AutoTrade 업무 규칙
- KIS Broker 연동 정책
- 투자 전략과 Risk Policy
- 실제 Project/Module/Database/Service 명세
- AutoForge가 만든 골격 위의 사용자 코드
- 운영 환경별 Secret reference
- 실제 통합 테스트와 배포 정책

## 참고 프로젝트별 채택 범위

### common-tool

가져올 것:

- 명세에서 Packet, Model, DB와 Application 연결을 생성하는 발상
- 반복 가능한 결정적 출력
- 테이블과 Load/Save 규칙을 한 출처에서 생성하는 방식

버릴 것:

- C# 전용 출력
- 저장 프로시저 강제
- 생성기와 대상 프로젝트의 강한 결합
- 사용자 코드를 안전하게 구분하지 않는 생성 방식

### game-server

가져올 것:

- Application, Domain Template와 Service 책임 분리
- Global/User/Log 데이터 역할
- 사용자 키 기반 수평 배치
- 서버 시작과 종료 수명주기

버릴 것:

- 고정 server ID와 thread count
- 로컬 mutex에 의존하는 분산 제어
- MySQL과 stored procedure에 고정된 업무 계층
- C++/C# 실행 모델을 Python에 그대로 번역하는 방식

### SKN12 base_server

가져올 것:

- FastAPI Router와 Domain별 Template 구조
- 실제 Account, Profile, Portfolio와 AutoTrade 요구사항
- async DB pool과 lifespan
- Redis namespace, TTL, Hash와 Rank 사용 경험
- Queue, retry, DLQ, Outbox와 분산 lock이 필요하다는 요구사항
- KIS API, WebSocket와 실시간 데이터 흐름

교체할 것:

- Template callback → Application Handler
- ServiceContainer singleton → dependency provider와 composition root
- 직접 만든 DB client → SQLAlchemy async Adapter
- 수작업 SQL 배포 → Alembic migration
- 직접 만든 Queue/DLQ → RabbitMQ
- 자체 Logger/Monitor → OpenTelemetry 기반 observability
- 평문 API key DB 저장 → Secret Provider reference

버릴 것:

- 고정 OTP secret과 고정 token
- 인증 검증 우회
- Global DB silent fallback
- giant `main.py`
- 문서에만 있고 실제 코드로 확인되지 않은 기능
- 임시 응답, mock business result와 운영상 위험한 기본값

## 필수 외부 서비스

### Redis

Redis는 `kis-auto-trading`의 필수 기반 Service다.

- cache
- 짧은 수명의 상태
- rate limit
- idempotency key
- 분산 coordination
- 실시간 데이터 보조

Redis는 영속 업무 데이터의 원장이 아니며 RabbitMQ를 대신하지 않는다.

### RabbitMQ

RabbitMQ는 필수 Queue Transport다.

- 비동기 작업 전달
- acknowledgment
- retry
- dead letter queue
- Worker 부하 분산

AutoForge의 in-process EventBus와 RabbitMQ의 외부 Transport는 분리한다.

```text
Domain Event
  → Outbox
  → RabbitMQ Publisher Adapter
  → Exchange/Queue
  → Worker Consumer
```

### Database

업무 원장은 관계형 DB에 저장한다. SQLAlchemy async와 Alembic을 기본 Adapter와
migration 도구로 사용한다. 물리 shard는 명세가 표현할 수 있게 유지하되 실제
부하가 확인되기 전에 강제하지 않는다.

## 코드 채택 절차

참고 코드를 적용할 때 다음을 기록한다.

1. 원본 파일과 기능
2. 원래 해결하려던 문제
3. 실제 구현 여부
4. 보존할 Domain 규칙
5. 교체할 Infrastructure
6. AutoForge 생성 영역
7. kis-auto-trading 사용자 소유 영역
8. 동작을 보존하는 테스트

금융 계산과 주문 규칙은 테스트 벡터 없이 임의로 변경하지 않는다.

## 개발 반복 과정

```text
참고 구현 분석
  → 범용 구조와 업무 규칙 분리
  → AutoForge 명세/Generator 구현
  → 격리 Workspace 생성
  → 테스트와 build
  → kis-auto-trading 적용
  → 실제 통합 테스트
  → 발견한 문제를 AutoForge에 환류
```

양쪽 저장소는 독립 Git 저장소로 유지하고 commit과 push도 각각 분리한다.
