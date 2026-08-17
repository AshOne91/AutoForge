# ADR-0001: 단일 호스트 Airflow scheduler HA는 LocalExecutor를 사용한다

## 상태

승인됨 — 아직 구현 전

## 맥락

현재 생성되는 Airflow local runtime은 PostgreSQL metadata database 위에서
`SequentialExecutor`와 scheduler 한 대를 사용한다. 이는 단순한 local 검증에는
적합하지만 scheduler process 장애를 견디지 못하고, `SequentialExecutor`는 한 번에
한 task만 실행하므로 HA 또는 production 실행 모델이 아니다.

AutoForge의 현재 local HA 범위는 Docker 한 호스트 안의 process/node recovery다.
Durable Job DAG는 직접 업무를 수행하지 않고 `(job_type, run_key)` idempotency key를
가진 token-protected API를 호출하며, 실제 업무는 Outbox와 worker가 수행한다.

## 결정

- Local Environment 명세에 `airflow_scheduler_replicas`를 추가한다. 기본값은 `1`이고,
  값이 `2` 이상이면 opt-in scheduler HA이다.
- scheduler HA는 `local_environment.enabled`, 하나 이상의 Durable Job,
  `postgres_mode: ha`를 요구한다. Airflow 2.10.5는 PostgreSQL 12+ metadata database의
  row-level lock으로 다중 scheduler를 조정하므로, 생성된 PostgreSQL HA writer endpoint를
  그대로 사용한다.
- scheduler HA에서는 `LocalExecutor`와 최소 두 개의 scheduler container를 생성한다.
  모든 scheduler는 같은 image, read-only DAG mount, metadata DB, 그리고 user-owned
  `AIRFLOW_FERNET_KEY`를 공유한다.
- `airflow-init` migration은 한 번만 실행한다. 각 scheduler는 독립 health endpoint와
  healthcheck를 가지며, host port를 추가로 공개하지 않는다.
- Durable Job API의 `(job_type, run_key)` idempotency는 Airflow DB lock과 별개인 두 번째
  업무 실행 방어선이다. scheduler failover가 API trigger 재시도를 만들더라도 같은 logical
  date의 Job은 하나만 생성되어야 한다.

## 결과

이 결정은 단일 Docker 호스트에서 scheduler 하나가 중단되어도 남은 scheduler가 DAG를
계속 조정하는 것을 검증할 수 있게 한다. 그러나 task executor process, Docker host,
shared DAG/log storage, PostgreSQL host 자체의 장애까지 해결하지는 않는다.

webserver replica와 public proxy, deferrable task용 triggerer HA, Celery/Kubernetes
executor, 다중 호스트 DAG 배포, 원격 task log storage는 이후 Kubernetes 또는 managed
deployment 계약이 소유한다. CeleryExecutor를 지금 도입하면 broker/worker 운영 계약을
Airflow에 중복 추가하게 되므로, 현재 Durable Job API trigger DAG에는 선택하지 않는다.

## 검증 기준

1. 두 scheduler가 같은 PostgreSQL HA metadata writer에 연결되고 각각 healthy가 된다.
2. scheduler 하나를 중단한 뒤 남은 scheduler가 새 DAG run을 처리한다.
3. 같은 logical date의 Durable Job은 하나만 생성된다.
4. 중단한 scheduler가 재기동해 cluster에 재합류한다.
5. 이 결과는 single-host process recovery로만 기록한다.

## 근거

Airflow 2.10.5는 PostgreSQL 12+에서 row-level lock으로 다중 scheduler를 지원하고,
단일 머신에는 `LocalExecutor`를 권장한다. scheduler별 health endpoint와 CLI health check도
지원한다.

- [Airflow 2.10.5 scheduler](https://airflow.apache.org/docs/apache-airflow/2.10.5/administration-and-deployment/scheduler.html)
- [Airflow 2.10.5 production deployment](https://airflow.apache.org/docs/apache-airflow/2.10.5/administration-and-deployment/production-deployment.html)
- [Airflow 2.10.5 health checks](https://airflow.apache.org/docs/apache-airflow/2.10.5/administration-and-deployment/logging-monitoring/check-health.html)
