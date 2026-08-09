# common-tool과 game-server 심층 분석

## 분석 목적

AutoForge는 `common-tool`의 C# 코드를 Python으로 번역하는 프로젝트가 아니다.
검증된 명세 하나에서 반복 구조를 만들고, 생성된 구조가 실제 Application에서
조립되는 원리를 계승하는 프로젝트다.

분석 기준 저장소는 다음과 같다.

- `C:\게임베이스툴\common-tool-master`
- `C:\게임베이스서버\game-server-master`
- `C:\SKN12-FINAL-2TEAM\base_server`

## common-tool의 실제 역할

`Program.cs`에는 table, template, database, sql, application, controller 생성
명령이 각각 존재한다. 따라서 common-tool은 문자열 템플릿 도구가 아니라 명세를
읽어 서버의 정적 구조와 런타임 연결을 함께 만드는 아키텍처 조립기다.

`InfraTemplateConfig`는 다음 정보를 하나의 출처로 관리한다.

- Template 이름, 종류와 버전
- Model과 Field
- Protocol ID, 방향, request/response/notification 방식
- Request, Response와 Notification Member
- Database 종류, Table 종류와 Partition Key
- Application이 사용할 Service와 Template

이 명세에서 다음 산출물이 파생된다.

```text
infrastructure-config.json
  ├─ Model / Packet / Protocol
  ├─ Controller callback
  ├─ Template / role-specific implementation 연결
  ├─ DBTable / UserDB / DBLoad / DBSave
  ├─ 물리 DB별 SQL
  └─ Application project / Entry / App / Controller 조립
```

## game-server에서 검증한 런타임 의미

game-server의 Template은 파일 생성용 템플릿이 아니다. Account, Item, Shop처럼
재사용 가능한 업무 모듈이자 사용자 상태와 생명주기를 가진 런타임 구성 단위다.

Account Template은 Master, Login, Game, User, Client 객체 역할에 따라 다른
구현을 연결하며 다음 Hook을 제공한다.

- `Init`, `OnLoadData`
- `OnClientCreate`, `OnClientDelete`, `OnClientUpdate`
- `OnSetNewbie`, `OnPlayerSelectPrepare`
- `OnTemplateUpdate`

Application 명세는 사용할 Service와 Template을 선택한다. 생성된 `App.cs`는
Template 등록, Controller callback 연결, 접속 객체 생성, Packet dispatch,
DB 저장과 종료 처리를 담당한다. Application은 단순 실행 파일이 아니라
Composition Root다.

## Account 수직 흐름

`CG_CREATE_PLAYER`는 명세의 Protocol ID와 request/response Member에서 Packet과
Controller가 생성된다. Controller는 Global DB에서 player key를 할당한 뒤 사용자
키로 선택한 Game DB에 플레이어를 만든다.

`CG_PLAYER_SELECT`는 user key와 player key로 사용자 Aggregate를 로드하고,
Account뿐 아니라 등록된 Template들의 준비 Hook을 실행한다. 완료 후 Global DB에
로그인 서버와 상태를 기록한다.

연결 종료 시에는 사용자 Template DB를 저장하고 Global 로그아웃 상태를 갱신한 뒤
Controller와 객체를 정리한다. 생성된 `DBSave`는 변경 표시가 없는 Table을 저장하지
않는다. 이는 단순 CRUD Repository보다 넓은 Aggregate Load/Save 정책이다.

## 계승할 원리

- 한 명세에서 API/Packet, Model, DB와 Application 연결을 함께 파생한다.
- 생성 결과는 입력이 같으면 결정적이어야 한다.
- Application은 선택한 Module과 Service를 조립한다.
- 업무 모듈은 생명주기와 저장 경계를 표현할 수 있어야 한다.
- Global 데이터와 사용자 Shard 데이터의 책임을 명시적으로 나눈다.
- 생성 코드와 사람이 작성할 코드는 안전한 확장 지점으로 분리한다.

## 현대화할 구현 방식

| 기존 방식 | AutoForge 방식 |
|---|---|
| C# partial class | GENERATED/SCAFFOLDED/USER_OWNED 파일 소유권 |
| 고정 callback wiring | 생성된 Router/Handler/Dependency wiring |
| 정적 TemplateContext | FastAPI lifespan과 명시적 Dependency Provider |
| ADO.NET과 저장 프로시저 고정 | 기술 중립 계약과 SQLAlchemy/DB Plugin |
| 자체 Socket Packet | HTTP, WebSocket, Queue별 Transport Plugin |
| 프로세스 내부 서버 상태 | Redis 등 외부 Shared State Adapter |
| 수동 SQL 배포 | 결정적 DDL과 Alembic migration 이력 |

## 그대로 복사하지 않을 부분

- C# 실행 모델과 정적 Context
- 특정 DB와 저장 프로시저에 대한 강한 결합
- 생성 코드와 사용자 수정 코드가 섞일 수 있는 경계
- 고정 서버 ID, Thread 수와 로컬 프로세스 전용 동기화
- 테스트 없이 이전 업무 동작을 임의로 재해석하는 방식

## AutoForge에 주는 설계 요구

현재 `ModuleSpec`의 Model, HTTP Endpoint, Table, Repository와 Data Placement는
올바른 첫 수직 단면이다. 다만 장기적으로 다음 요구를 표현할 확장 지점이 필요하다.

- HTTP 외 Message/Event 계약과 안정적인 Operation 식별자
- Application 또는 Worker별 Module 배치
- Module의 Service 의존성과 생명주기
- 사용자 Aggregate 단위 Load/Save와 Transaction 경계
- Global/Shard routing과 실패 정책
- Redis, RabbitMQ와 외부 Service capability

이 항목은 현재 명세 버전에 한꺼번에 추가하지 않는다. kis-auto-trading의 실제
로그인 수직 흐름을 생성하면서 필요한 최소 계약만 검증 후 도입한다.
## 실제 서비스 구조 대조 결과

실제 소스를 대조하면 계보는 다음과 같다.

```text
common-tool 명세
  -> generated model / protocol / table / SQL
  -> Application composition
  -> Template runtime module
  -> Service adapter와 lifecycle
```

`gameserver`의 `TemplateStartup`은 여러 Template와 DB·Cache·Event·MessageQueue를 순서대로 등록한다. Controller는 Template protocol callback으로 연결되고, Template이 업무 동작과 저장 경계를 소유한다. 따라서 AutoForge의 `ModuleSpec`은 단순 router 생성 설정이 아니라, 향후 transport·persistence·service capability를 함께 묶는 조립 단위로 유지해야 한다.

계승하지 않을 구현은 전역 정적 Context/ServiceContainer, 생성 코드에 업무 규칙을 직접 넣는 방식, 특정 DB stored procedure와 C# 실행 모델에 대한 강결합이다. Python에서는 GENERATED 산출물과 SCAFFOLDED handler를 분리하고, 명시적 provider/lifespan과 Global/Shard placement 계약을 사용한다.

첫 확장 계약은 일반적인 Template 프레임워크가 아니라 KIS 뉴스 수집의 Durable Job 수직 슬라이스다. Job 상태·멱등성·Outbox·Worker·Airflow trigger/status를 실제 consumer로 검증한 뒤 필요한 공통 필드만 Module/Application 명세에 추가한다.
