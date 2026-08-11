# Scheduled Ingestion Blueprint

이 Blueprint는 반복 실행되는 외부 데이터 수집의 공통 실행 기반을 생성한다.

- PostgreSQL durable-job store와 migration
- RabbitMQ transport와 transactional outbox
- Airflow DAG, outbox relay, durable-job worker
- private durable-job API와 Docker Compose 실행 환경

생성 명령:

```powershell
python -m autoforge.main generate --project blueprints/scheduled_ingestion/autoforge.yaml --specifications blueprints/scheduled_ingestion/specifications --output C:\work\ingestion-server
```

생성 후 `src/ingestion_server/application/durable_job_handler.py`를 구현한다.
이 SCAFFOLDED handler가 뉴스·공시·시장 데이터 등 소비자별 수집 업무를 소유한다.

Airflow는 실행 시점과 재시도를 조율할 뿐, 수집 업무를 직접 구현하지 않는다. API key,
외부 API adapter, 수집 대상, 저장 모델과 오류 정책은 소비자 프로젝트의 책임이다.
