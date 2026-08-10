# 환경 실현과 통합 검증 계약

## 목적

AutoForge는 개발자 PC나 운영 환경에 서드파티를 임의로 설치하지 않는다. 대신
프로젝트 명세가 선언한 런타임 의존성을 로컬 개발, 통합 테스트, 운영 환경에서
재현할 수 있는 계약과 산출물로 변환한다.

이는 현재의 앱 빌드 전용 Dockerfile 책임을 유지하면서, PostgreSQL, Redis,
RabbitMQ, Airflow가 실제로 연결되는지를 단계적으로 검증하기 위한 계약이다.

## 반드시 분리할 네 가지 범위

| 범위 | 책임 | 예시 |
| --- | --- | --- |
| AutoForge 제어면 | 생성·검증 작업 자체 | JobStore, Git 작업자 |
| 생성 애플리케이션 런타임 | 명세가 선택한 앱 의존성 | PostgreSQL, Redis Session, RabbitMQ |
| 개발·통합 환경 | 재현 가능한 로컬 실행 | Docker Compose, 임시 테스트 DB |
| 운영 환경 | 가용성·보안·비용 결정 | RDS, Redis Cluster, RabbitMQ HA, MWAA |

이 범위는 같은 서비스를 사용하더라도 하나의 설정 파일이나 하나의 Generator로
합치지 않는다. 특히 AutoForge 제어면의 인프라 선택이 생성 애플리케이션의
운영 토폴로지를 결정해서는 안 된다.

## 현재 확정된 출발점

- `DatabaseStoreSpec`, `ServiceSpec`, `DurableJobSpec`은 애플리케이션의 기능과
  연결 환경변수 계약을 표현한다.
- Dockerfile Generator는 생성 애플리케이션의 빌드만 담당한다.
- Redis Session과 RabbitMQ Outbox는 생성 계약과 단위 테스트가 있다.
- Airflow는 Durable Job `schedule`이 있을 때 DAG 소스와 local runtime을 생성한다.

Compose Generator와 KIS local/integration profile은 있다. Durable Job이 선언되면
고정된 Airflow 실행 이미지와 paused DAG 런타임도 생성된다. Airflow의 운영용
scheduled 배포 Generator와 애플리케이션 컨테이너 조합은 아직 없다. 이는 운영
토폴로지를 추측하지 않기 위한 의도된 경계다.

## 향후 환경 profile의 역할

환경 profile은 ServiceSpec을 대체하지 않는다. 이미 선언된 서비스를 어떤 환경에서
어떻게 실현하고 검증할지 선택한다.

| Profile | 기본 구성 | 사용 목적 | 운영 토폴로지 포함 여부 |
| --- | --- | --- | --- |
| `local` | PostgreSQL, Redis standalone, RabbitMQ | 개발자 재현 | 아니오 |
| `integration` | 격리된 임시 서비스 | 실제 I/O 회귀 테스트 | 아니오 |
| `scheduled` | local/integration + Airflow | Durable Job DAG 검증 | local profile에서만 |
| `production` | 외부 서비스 endpoint와 Secret 참조 | 운영 배포 문서·검증 | 예, 별도 선택 |

Redis Cluster/Sentinel, DB 복제, RabbitMQ HA, Kubernetes, AWS는 `local`의 기본값이
아니다. 실제 소비자 요구와 해당 운영 profile이 선택된 뒤 별도 Generator 또는
deployment plugin으로 다룬다.

## 생성 산출물과 소유권

향후 Environment Generator를 도입할 때의 기본 경계는 다음과 같다.

```text
generated-owned
  environment/autoforge.compose.yml
  environment/.env.example
  docs/generated-environment.md

user-owned
  environment/compose.override.yml
  .env
  운영 provider별 Secret과 접근 정책
```

`.env.example`에는 변수 이름, 포트, 비밀값이 아닌 예시만 남긴다. 실제 주소,
비밀번호, 토큰, 인증서와 cloud credential은 Git 추적 파일이나 AutoForge manifest에
기록하지 않는다.

## 구현과 실제 검증 순서

1. **소비자 명세 선택**: KIS가 Durable Job, coordinator용 Global DB, 필요한 서비스와
   schedule을 선언한다. 샤드 DB를 Job coordinator로 추측해 사용하지 않는다.
2. **환경 계약 설계**: 선택된 명세에서 필요한 local/integration 서비스와 환경변수를
   결정한다. 이때 Compose 파일 형식·이미지 버전·volume 경계를 명시한다.
3. **Environment Generator 최소 구현**: 선언된 서비스만 대상으로 Compose,
   `.env.example`, 실행 문서를 생성한다. 사용자 override와 실제 Secret은 보존한다.
4. **서비스 기동 검증**: 생성된 Compose로 DB migration, FastAPI health check,
   Redis 연결, RabbitMQ topology 선언을 확인한다.
5. **수직 통합 검증**: `trigger API -> JobRecord + Outbox -> RabbitMQ -> Worker ->
   status API`를 실제 컨테이너에서 검증한다.
6. **Airflow 검증**: 5단계가 통과한 뒤 DAG import와 runtime health를 먼저 검증하고,
   애플리케이션 컨테이너가 연결되면 trigger, polling, retry, timeout을 검증한다.
   내부 API는 private network와 service identity를 전제로 한다.
7. **CI 재현**: 단위 테스트와 컨테이너 통합 테스트를 분리해 CI에서 반복한다.
8. **운영 profile 확장**: HA, Cluster, cloud provider, Kubernetes는 실제 부하·보안·
   비용 요구가 확인된 뒤 도입한다.

## 각 단계의 통과 기준

| 단계 | 통과 기준 |
| --- | --- |
| 1 | 명세 검증과 ownership 경계가 명확함 |
| 3 | 같은 명세에서 결정적인 환경 파일이 생성됨 |
| 4 | 컨테이너 헬스체크와 migration이 성공함 |
| 5 | 중복 trigger가 하나의 Job으로 수렴하고 실패가 상태·DLQ 경로에 남음 |
| 6 | 같은 data interval의 Airflow 재시도가 중복 업무를 만들지 않음 |
| 7 | 깨끗한 CI 환경에서 4~6을 선택적으로 재현함 |

## 현재 다음 행동

현재 KIS에는 `news_collection` Durable Job 선언, `automation` coordinator Global DB,
그리고 local/integration Compose profile이 있다. Durable Job 내부 API는
`DURABLE_JOB_API_TOKEN` 기반의 private service identity를 생성하며, Airflow
컨테이너가 이 토큰과 생성 DAG를 주입받아 Healthy 상태로 기동되는 것까지 검증했다.
생성된 migration과 애플리케이션 컨테이너도 Healthy 상태로 검증했다. Airflow는
같은 Compose 네트워크에서 인증된 trigger와 status 조회를 수행했고, 무인증 요청은
401로 거부됐다. Compose application profile은 같은 local image에서 Outbox relay와
durable-job worker도 기동한다. Worker는 기존 RabbitMQ transport를 재사용하되
`<service-queue>.durable-jobs` 전용 큐에 Durable Job event type만 bind한다.

2026-08-10 실제 Compose 검증에서 `news_collection` 요청은 Outbox와 RabbitMQ를
거쳐 `failed` 상태로 전이했다. 이는 사용자 소유 `ApplicationDurableJobHandler`가
명시적으로 미구현 예외를 내기 때문이며, 인프라 실패가 아니다. 해당 handler가 실제
업무를 구현하면 같은 경로는 `succeeded` 상태를 만든다.
