# Scheduled Ingestion Blueprint

이 문서는 이 Blueprint의 입력·생성 방법과 소비자 소유 경계만 설명한다. 전체
명세·Event/Pipeline·환경 계약은
[`specification_design.md`](../../docs/architecture/specification_design.md),
[`event_driven_architecture.md`](../../docs/architecture/event_driven_architecture.md),
[`environment_validation_contract.md`](../../docs/architecture/environment_validation_contract.md)를 따른다.

이 Blueprint는 반복 실행되는 외부 데이터 수집의 공통 실행 기반을 생성한다.

- PostgreSQL durable-job store와 migration
- RabbitMQ transport와 transactional outbox
- Airflow DAG, outbox relay, durable-job worker
- private durable-job API와 Docker Compose 실행 환경

이 Blueprint는 RAG 소비자 연결도 선택했으므로 기본 통합 환경을 시작하기 전에
생성된 `deploy/rag/README.md`에 따라 공유 네트워크와 RAG·inference profile을
먼저 시작한다. 모델 다운로드는 별도이며 기본 시작 조건이 아니다.

생성 명령:

```powershell
python -m autoforge.main generate --project blueprints/scheduled_ingestion/autoforge.yaml --specifications blueprints/scheduled_ingestion/specifications --output C:\work\ingestion-server
```

생성 후 `src/ingestion_server/application/durable_job_handler.py`를 구현한다.
이 SCAFFOLDED handler가 뉴스·공시·시장 데이터 등 소비자별 수집 업무를 소유한다.

Airflow는 실행 시점과 재시도를 조율할 뿐, 수집 업무를 직접 구현하지 않는다. API key,
외부 API adapter, 수집 대상, 저장 모델과 오류 정책은 소비자 프로젝트의 책임이다.
