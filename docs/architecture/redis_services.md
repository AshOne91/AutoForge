# Redis 공통 서비스 아키텍처

## 목적

AutoForge가 생성하는 Application은 Redis client를 Handler와 Domain에서 직접
호출하지 않는다. Application은 작은 기술 중립 Protocol에 의존하고 Redis는 그
Protocol을 구현하는 Infrastructure Adapter다.

Redis 기능을 하나의 거대한 `RedisService`로 합치지 않는다. 이 문서는 로그인
세션과 TTL을 소유하는 `SessionStore` 계약만 정의한다. 다른 사용 사례는
`SessionStore`에 기능을 추가하지 않고 별도 계약을 가져야 한다.

## SessionStore 계약

```text
create(session)
get(session_id)
refresh(session_id)
revoke(session_id)
revoke_user_sessions(user_id)
```

명세 예시는 다음과 같다.

```yaml
application:
  framework: fastapi
  modules:
    - identity
    - account
  services:
    - name: session
      kind: redis_session
      namespace: kis_session
      ttl_seconds: 3600
```

`namespace`와 TTL은 명세에 기록할 수 있지만 Redis 주소, 비밀번호와 TLS 인증서는
런타임 Secret으로 주입한다.

## 생성 결과

```text
infrastructure/session_store/
├── protocol.py   SessionData, SessionStore와 명시적 오류
├── fake.py       Redis 없이 Application을 검사하는 TTL 지원 Fake
└── redis.py      redis.asyncio 기반 Adapter
```

프로젝트가 `redis_session`을 선택한 경우에만 Redis Python 의존성을 생성한다.

## Redis Key와 TTL

```text
<namespace>:session:<session_id>
<namespace>:user-sessions:<user_id>
```

세션 본문은 개별 TTL key에 저장한다. 사용자별 Set은 중복 로그인 차단이나 모든
세션 폐기에 사용한다. create와 refresh는 Redis transaction pipeline을 사용해
세션 key와 사용자 index의 수명을 함께 갱신한다.

Redis는 세션의 빠른 조회와 폐기를 담당하지만 계정과 개인정보의 영속 원장은
아니다. Global identity와 Sharded profile은 관계형 DB에 남는다.

## 장애 정책

- Redis 연결 오류를 로그인 성공이나 세션 없음으로 위장하지 않는다.
- Adapter는 Redis 예외를 `SessionStoreError`로 변환한다.
- Handler가 fail-open 또는 fail-closed 정책을 명시적으로 결정한다.
- 인증 세션의 기본 정책은 fail-closed다.
- Fake는 테스트 편의를 위해 장애를 숨기는 구현이 아니라 동일한 TTL과 폐기 계약을
  검증하는 구현이다.

## Topology

`ServiceSpec.mode`는 `standalone`, `sentinel`, `cluster`를 구분한다. 생성된
provider는 각각 `url_env`, `sentinel_urls_env`와 `sentinel_master`, 또는
`cluster_url_env`와 `cluster_startup_nodes_env`를 사용한다. 연결 주소와 credential은
명세나 생성 코드에 넣지 않고 런타임 환경에서 주입한다. `cluster_url_env`는 기본
연결 URL이고, `cluster_startup_nodes_env`는 쉼표로 구분한 Redis URL 목록이다. 후자는
기본 시드 노드가 장애여도 새 client가 다른 노드에서 cluster map을 다시 얻도록 한다.

Topology 선택은 `SessionStore` Protocol을 바꾸지 않는다. 로컬 환경 Generator는
standalone과 cluster를 실현하며 sentinel을 standalone으로 묵시적으로 대체하지
않는다.

로컬 `cluster` 환경의 고정 기준선은 7000–7005의 여섯 Redis 노드다. 초기화기는
`--cluster-replicas 1`로 세 primary와 세 replica를 만들고, 각 노드의 `/data`를
명명된 Compose volume에 보존한다. 이는 한 Redis container 장애 뒤 slot failover를
검증하기 위한 로컬 기준선이다. 모든 노드가 같은 Docker host에 있으므로 host 또는
가용 영역 장애까지 격리하는 운영 HA 설계는 아니다.

`ServiceSpec.mode`는 생성 애플리케이션의 연결 의미를 선택할 뿐, 운영 Redis
provider나 배포 토폴로지를 선택하지 않는다. 소비 프로젝트가 provider와 가용성
요구사항을 명시하기 전까지 AutoForge는 runtime Secret의 연결 계약만 생성하며,
ElastiCache·MemoryDB·Sentinel·Redis StatefulSet 같은 provider별 운영 Redis
manifest는 생성하지 않는다. `cluster`를 Sentinel로 묵시적으로 대체하지 않는 것과
같이, 로컬 Compose Cluster를 운영 배포 모델로 묵시적으로 승격하지 않는다.

`ServiceSpec.mode`는 생성 애플리케이션의 연결 의미를 선택할 뿐, 운영 Redis
provider나 배포 토폴로지를 선택하지 않는다. 소비 프로젝트가 provider와 가용성
요구사항을 명시하기 전까지 AutoForge는 runtime Secret의 연결 계약만 생성하며,
ElastiCache·MemoryDB·Sentinel·Redis StatefulSet 같은 provider별 운영 Redis
manifest는 생성하지 않는다. `cluster`를 Sentinel로 묵시적으로 대체하지 않는 것과
같이, 로컬 Compose Cluster를 운영 배포 모델로 묵시적으로 승격하지 않는다.

## FastAPI 수명주기와 Dependency

`redis_session`을 선택한 Project에는 다음 연결 코드도 생성한다.

```text
FastAPI lifespan 시작
  → url_env가 가리키는 환경변수 확인
  → Redis async client 생성 (cluster는 다중 시작 노드 사용)
  → RedisSessionStore를 app.state에 등록

HTTP Handler
  → get_session_store(Request)
  → SessionStore Protocol 반환

FastAPI lifespan 종료
  → app.state에서 SessionStore 제거
  → Redis client aclose
```

환경변수가 없으면 Application 시작을 실패시킨다. 인증용 Session Service를 조용히
비활성화하면 Replica마다 동작이 달라질 수 있기 때문이다. 테스트는 실제 Secret을
파일에 저장하지 않고 `url_env`에 임시 URL을 주입하거나 Redis factory를 Fake로
교체한다.
## Endpoint dependency specification

Redis session을 사용하는 endpoint는 Module 명세에 의존성을 명시한다.

```yaml
endpoints:
  - name: login
    dependencies:
      - session_store
```

이 선언은 생성된 FastAPI router가 `get_session_store`를 `Depends`로 호출하고,
얻은 `SessionStore` Protocol을 사용자 소유 handler 인자로 전달하게 한다. Handler는
Redis client나 `app.state`를 직접 알지 않으므로 Application과 Infrastructure 경계가
유지된다. 하나 이상의 endpoint가 `session_store`를 요구하면 Project 명세에도
`redis_session` service가 반드시 있어야 하며, CLI는 파일을 쓰기 전에 이를 검증한다.
