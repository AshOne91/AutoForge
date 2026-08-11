# Identity Session Profile Blueprint

이 Blueprint는 FastAPI 기반 서버의 첫 공통 기반을 생성한다.

- Global Identity PostgreSQL store
- Redis Cluster session contract
- `user_id`로 라우팅되는 sharded Profile PostgreSQL store
- GENERATED router, schema, persistence와 SCAFFOLDED handler 경계

생성 명령:

```powershell
python -m autoforge.main generate --project blueprints/identity_session_profile/autoforge.yaml --specifications blueprints/identity_session_profile/specifications --output C:\work\my-server
```

생성 후 `src/base_server/modules/*/handlers.py`를 구현한다. 이 파일은 SCAFFOLDED
소유권이므로 재생성해도 사용자 업무 구현을 덮어쓰지 않는다.

의존 서비스 환경도 생성된다.

```powershell
Copy-Item C:\work\my-server\environment\.env.example C:\work\my-server\environment\.env
docker compose --env-file .env -f compose.integration.yml up -d --wait
```

이 환경은 PostgreSQL과 Redis Cluster, migration, FastAPI application 컨테이너를
함께 기동한다. durable-job, Airflow, RabbitMQ는 이 Blueprint 범위 밖이며 별도
Application 조합에서 활성화한다.

비밀번호 해싱, 토큰 형식, 권한, `user_id`에 대한 shard 선택 규칙은 이 Blueprint에
포함하지 않는다. 해당 보안·업무 정책은 소비자 프로젝트가 소유한다.
