# 참고 프로젝트 적용 전략

> **문서 역할: REFERENCE**
> 이 문서는 참고 프로젝트의 계보와 비교 기준을 보존한다. 현재 AutoForge
> Architecture나 구현 상태를 정의하지 않으며, 현재 계약은
> [`system_design.md`](../architecture/system_design.md)와 각 Canonical Architecture,
> 구현 상태와 계획은 [`.codex/current_status.md`](../../.codex/current_status.md)와
> [`.codex/roadmap.md`](../../.codex/roadmap.md)를 따른다.

## 목적

AutoForge와 `kis-auto-trading`은 이미 검증된 참고 프로젝트의 구조와 문제 해결
경험을 활용한다. 참고 코드를 무조건 복사하거나 반대로 모두 새로 만들지 않는다.

이 문서는 각 프로젝트를 분석할 때 사용한 역할과 코드 채택 기준을 기록한다.

## 프로젝트 관계

```text
common-tool
  → 무엇을 자동 생성해야 하는지 보여주는 생성기 원형

game-server
  → 생성된 Application, Domain, Service와 DB가 어떻게 조립되는지 보여주는 실행 원형

SKN12 base_server
  → AutoForge가 있었다면 생성·조립했을 FastAPI 서비스의 롤모델

JavaBaseWebServer
  → C# 구조를 Spring Boot, MySQL과 Redis로 옮긴 서비스 조립 참고 구현

AutoForge
  → 반복 구조와 외부 서비스 연결을 명세에서 생성하고 검증하는 플랫폼

kis-auto-trading
  → AutoForge를 사용해 SKN12 기능을 현대화하는 실제 서비스
```

SKN12는 AutoForge의 소스 코드가 아니다. SKN12가 해결하려던 요구사항과 실제
동작하는 Domain 흐름을 AutoForge 명세와 Generator의 검증 사례로 사용한다.

KIS의 Proxy/App/Secret 분리, Kubernetes 토폴로지와 AutoForge 생성 경계는
`kis_ha_reference_blueprint.md`에 별도로 고정한다.

## 분석 당시 AutoForge 목표 역할

다음 목록은 참고 프로젝트 분석으로 도출한 목표 범위이며 현재 구현 목록이나
독립적인 Generation Contract가 아니다.

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

## 분석 당시 kis-auto-trading 역할

`kis-auto-trading`은 다음을 소유한다.

- Account/Profile, Portfolio, Order와 AutoTrade 업무 규칙
- KIS Broker 연동 정책
- 투자 전략과 Risk Policy
- 실제 Project/Module/Database/Service 명세
- AutoForge가 만든 골격 위의 사용자 코드
- 운영 환경별 Secret reference
- 실제 통합 테스트와 배포 정책

## 참고 프로젝트별 채택 범위

### 개념 대응표

| common-tool/game-server | base_server | AutoForge 목표 |
|---|---|---|
| Infrastructure Config | 수작업 Model/Protocol 설정 | 버전이 있는 Specification |
| Application | FastAPI application/main | Composition Root 생성 |
| Template | Domain별 template package | 재사용 가능한 Module 계약 |
| Packet/Protocol | Pydantic request와 Protocol | Transport별 Message/API 계약 |
| Controller callback | Router → Protocol → TemplateImpl | Router/Consumer → Handler |
| UserDB, DBLoad/DBSave | DatabaseService와 직접 Query | Repository/UoW와 DB Adapter |
| Global/Game DB | Global/Shard pool | DataPlacement와 ShardRouter |
| partial class | 사람이 수정하는 Impl | 파일 소유권과 보존 Manifest |

이 표는 이름을 그대로 복사하기 위한 것이 아니다. 기존 구조가 해결한 책임을
Python과 FastAPI에서 어떤 경계로 보존할지 판단하는 기준이다.

### common-tool

가져올 것:

- 명세에서 Packet, Model, DB와 Application 연결을 생성하는 발상
- 반복 가능한 결정적 출력
- 테이블과 Load/Save 규칙을 한 출처에서 생성하는 방식
- Protocol ID·방향·형식과 Application 연결까지 명세에서 파생하는 방식
- 생성된 공통 코드와 사람이 구현할 callback 확장 지점의 분리

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
- Template을 업무 모듈이자 런타임 구성 단위로 사용하는 방식
- Master/Login/Game처럼 Application 역할별로 Module을 다르게 조립하는 방식
- 사용자 Aggregate를 Template별로 로드하고 변경된 데이터만 저장하는 방식

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
- Router → Protocol → TemplateImpl로 이어지는 실제 업무 호출 경로
- Global shard 설정과 사용자 shard mapping을 분리한 DB routing
- 서비스 초기화 역순으로 종료하는 수명주기 의도

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

## 실제 소스 검증으로 확정한 방향

`common-tool`은 템플릿 파일을 복사하는 도구가 아니라, 명세에서 모델·프로토콜·DB·SQL·Application 조립물을 함께 파생하는 생성기다. `gameserver`의 Application은 필요한 Template와 Service를 Composition Root에서 조립하고, Template은 상태·수명주기·저장 경계를 가진 기능 모듈로 동작한다.

`base_server`는 이 계보를 FastAPI와 async lifecycle로 옮긴 운영 참고 구현이다. 다만 전역 `ServiceContainer`와 정적 서비스 접근은 그대로 계승하지 않고, AutoForge에서는 명시적 dependency provider와 lifespan으로 대체한다.

### JavaBaseWebServer

가져올 것:

- Application 시작 시 DB/Redis Pool과 Template을 명시적으로 조립하는 방식
- Hikari/Jedis Pool을 Service Adapter 뒤에 두는 방식
- 로그인 SessionInfo, TTL과 로그아웃 Session 폐기 흐름
- 로컬/debug/운영 설정을 분리하려는 의도

교체할 것:

- 평문 JSON Secret → 환경변수와 Secret Provider
- 넓은 ICacheClient → 역할별 작은 Protocol
- 오류를 false/null/0으로 숨기는 처리 → 명시적 Adapter 오류
- MySQL/JPA 고정 → Provider별 Plugin과 기술 중립 계약

상세 분석은 `java_base_web_server_analysis.md`를 따른다.

`base_server`의 Profile은 현재 Global DB procedure를 사용하고 Portfolio와 투자
계좌는 Shard DB를 사용한다. 새 `kis-auto-trading`에서는 로그인 식별정보만
Global에 두고 개인정보 Profile을 Shard에 두려는 목표가 있으므로, 이 차이는
복사 과정에서 숨기지 않고 명시적인 배치 정책 변경으로 취급한다.

## 생성 경계와 연결

기존 C#의 partial class는 생성 코드와 사용자 확장 코드를 분리하려는 참고
사례다. AutoForge가 채택한 정확한 GENERATED/SCAFFOLDED/USER_OWNED 규칙은
[`generation_contract.md`](../architecture/generation_contract.md)가 소유한다.

## 참고 프로젝트에서 도출한 Runtime 요구

다음 항목은 KIS 소비자 요구 분석이며 모든 생성 프로젝트에 강제되는 기본값이
아니다. 실제 Service 선택은 ProjectSpec과 각 Canonical Architecture를 따른다.

### Redis

Redis는 `kis-auto-trading`의 필수 기반 Service다.

- cache
- 짧은 수명의 상태
- rate limit
- idempotency key
- 분산 coordination
- 실시간 데이터 보조

Redis는 영속 업무 데이터의 원장이 아니며 RabbitMQ를 대신하지 않는다.
구체적인 SessionStore 계약은
[`redis_services.md`](../architecture/redis_services.md)를 따른다.

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
