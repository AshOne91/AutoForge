# JavaBaseWebServer DB와 Redis 분석

## 분석 대상

`C:\JavaBaseWebServer`는 C# game-server 구조를 Spring Boot로 옮기면서 DB와 Redis를
직접 구성한 참고 구현이다. 실제 접속정보가 포함되어 있으므로 이 문서에는 값을
기록하지 않고 구조와 검증 결과만 남긴다.

## 확인된 구성

- Database: MySQL 8 Connector
- Connection Pool: HikariCP
- ORM/Transaction: JPA, Hibernate와 `JpaTransactionManager`
- Cache: Redis standalone
- Java Redis client: Jedis Pool
- Session TTL: 3600초
- DB schema 자동 변경: `hibernate.hbm2ddl.auto=none`

Application은 Spring의 DB·Redis 자동 설정을 끄고 JSON 설정을 읽어 Pool과 공통
Service를 직접 조립한다. 이는 기존 C#의 명시적 Application 조립 방식을 보존하려는
구조다.

## 실제 연결 검증

2026-07-31 기준으로 다음을 확인했다.

- 일반 설정의 DB/Redis endpoint: TCP 도달 불가
- debug 설정의 MySQL endpoint: TCP 연결과 자격증명 인증 성공
- debug 설정의 MySQL schema: `SELECT 1` 성공
- debug 설정의 Redis endpoint: `PING/PONG` 성공
- Redis password: 현재 설정하지 않음

실제 host, database, username과 password는 원본 debug JSON에만 남기며 AutoForge
문서, Specification, Manifest와 Git 추적 환경파일로 복사하지 않는다.

## Java 로그인 Session 흐름

Account Template은 로그인 후 SessionInfo를 만들고 Redis UserHash와 access token
기반 Session을 저장한다. 로그아웃에서는 access token과 SessionInfo key를 삭제하고
DB의 logout time과 access token 상태를 갱신한다.

기존 Redis client는 String, Hash, Sorted Set과 List를 하나의 넓은 인터페이스로
제공하며 많은 오류를 `false`, `null`, `0`으로 바꾼다. 이 방식은 호출이 단순하지만
인증 경로에서 Redis 장애와 “세션 없음”을 구별하기 어렵다.

AutoForge는 다음처럼 책임을 좁힌다.

```text
Java ICacheClient
  ├─ String/Hash/List/SortedSet/Session
  └─ 오류를 기본값으로 변환

AutoForge
  ├─ SessionStore
  ├─ CacheStore (후속)
  ├─ RateLimitStore (후속)
  └─ Redis 오류를 명시적 Adapter 오류로 변환
```

## KIS 적용 판단

Java DB는 MySQL이고 현재 kis-auto-trading의 생성 Persistence는 PostgreSQL과
asyncpg 기준이다. 따라서 Java의 MySQL DSN과 계정을 KIS DB 설정으로 복사하지
않는다. 필요하다면 향후 MySQL Provider Plugin의 실제 통합 테스트 기준으로 쓴다.

Java Redis는 제품과 역할이 KIS SessionStore 목표와 호환되므로 로컬 통합 테스트에
재사용한다. Redis endpoint와 비밀번호는 다음 런타임 환경변수로만 주입한다.

```text
REDIS_URL
SESSION_TTL_SECONDS
```

운영 환경에서는 Kubernetes Secret 또는 선택한 Secret Provider가 값을 공급한다.
