# Redis 공통 서비스 아키텍처

## 목적

AutoForge가 생성하는 Application은 Redis client를 Handler와 Domain에서 직접
호출하지 않는다. Application은 작은 기술 중립 Protocol에 의존하고 Redis는 그
Protocol을 구현하는 Infrastructure Adapter다.

Redis 기능을 하나의 거대한 `RedisService`로 합치지 않는다.

```text
SessionStore       로그인 세션과 TTL
CacheStore         재계산 가능한 조회 결과
IdempotencyStore   중복 요청 차단
DistributedLock   분산 임계 구역
RateLimitStore     요청 빈도 제한
```

현재 첫 구현은 `SessionStore`만 지원한다. 나머지는 실제 수직 흐름에서 필요할 때
각각 독립 계약으로 추가한다.

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

## 아직 구현하지 않은 범위

- 실제 Redis Engine을 FastAPI lifespan에서 생성하고 종료하는 Provider
- JWT 또는 opaque access token 발급
- refresh token rotation
- 분산 lock, rate limit과 idempotency Adapter
- Redis Cluster/Sentinel topology
- 실제 Redis 통합 테스트

다음 단계는 이 SessionStore를 kis-auto-trading 명세에 적용하고, 생성된 Fake를
사용해 로그인 Application Handler의 성공·실패 흐름을 먼저 검증하는 것이다.
