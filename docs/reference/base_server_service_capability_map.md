# Base Server 서비스 역량 지도

기준일: 2026-08-11

> **문서 역할: SNAPSHOT / REFERENCE**
> 이 표의 “현재”, “완료”, “다음”은 2026-08-11 당시 판단을 뜻한다. 최신 구현
> 상태나 Roadmap의 정본으로 사용하지 않는다. 최신 정보는
> [`.codex/current_status.md`](../../.codex/current_status.md),
> [`.codex/roadmap.md`](../../.codex/roadmap.md),
> [`.codex/next_task.md`](../../.codex/next_task.md)를 따른다.

## 목적

AutoForge의 목표는 `base_server` 코드를 복사하는 것이 아니다. 검증된
`base_server`의 **서비스 책임**을 현재의 Python/FastAPI, 명세 기반 생성,
명시적 ownership 구조로 다시 구현하는 것이다.

하나의 Application은 필요한 역량만 선택한다. 모든 생성 프로젝트에 모든
컨테이너와 SDK를 넣지 않는다. 이 원칙은 common-tool의 “명세에서 연결된
구조를 생성한다”는 의도와, game-server의 “Application이 필요한 Service와
Template를 조합한다”는 런타임 의미를 보존한다.

## 용어

- **공통 생성 역량**: AutoForge가 명세와 생성기로 관리하고 재사용하는 경계.
- **Blueprint**: 여러 공통 역량을 한 사용 사례로 조합한 검증 가능한 입력.
- **SCAFFOLDED**: 생성은 한 번만 하고 이후 업무 구현은 소비자 프로젝트가 소유하는 파일.
- **도메인 구현**: 뉴스 수집, 주문 판단, 메시지 문구처럼 제품마다 달라 AutoForge가 소유하지 않는 코드.

## 전체 서비스 매핑

| Base Server 서비스 | 원래 책임 | AutoForge의 현재 상태 | 다음 귀속 |
| --- | --- | --- | --- |
| `core` | 설정, lifecycle, 로그, 모니터 | 부분 완료 | 명시적 lifespan/config/logging 계약을 공통 생성기로 유지 |
| `net` | FastAPI, middleware, HTTP 경계 | 완료 | FastAPI application/router 생성기로 유지 |
| `db` | Global/Shard DB, 연결, SQL | PostgreSQL 완료 | MySQL은 소비자 요구가 생길 때 provider로 추가 |
| `cache` | Redis cache/session/pool | session·cluster 및 generated key-value contract 완료 | consumer가 실제 key/value·TTL·무효화 정책을 선택할 때 조합 |
| `security` | 인증, 토큰, 비밀번호 보안 | identity/session 기준선 완료 | credential·권한 정책은 SCAFFOLDED 소비자 코드 |
| `event` | 프로세스 내부 이벤트 | EventBus 기반 완료 | application event 계약은 Blueprint별로 추가 |
| `queue` | 비동기 메시지 전달 | RabbitMQ 기반 완료 | durable job/outbox와 함께 생성 |
| `outbox` | DB 변경과 메시지의 일관성 | 완료 | durable-job Blueprint의 공통 기반 |
| `scheduler` | 주기 실행 | Airflow 생성·런타임 검증 완료 | 실제 일정과 업무 handler는 소비자 소유 |
| `lock` | 분산 잠금 | AutoForge generated lease contract 완료 | 실제 경쟁 구간이 consumer에서 선택될 때 lock key·TTL·업무 정책을 연결 |
| `external` | 외부 HTTP/API, retry, rate limit | AutoForge generated HTTP contract 완료 | 공급자별 adapter와 정책은 소비자 코드, 재사용 transport 계약만 제공 |
| `websocket` | 연결·채널·broadcast | 미구현 | 실제 Realtime 소비자가 생기면 Redis 확장형 Blueprint로 구현 |
| `notification` | WebSocket/email/SMS 알림 | 미구현 | 전달 채널은 공통화, 수신자·문구·업무 정책은 소비자 소유 |
| `email` | 이메일 전달 | 미구현 | notification 사용 사례가 확정된 뒤 provider adapter로 추가 |
| `sms` | SMS 전달 | 미구현 | notification 사용 사례가 확정된 뒤 provider adapter로 추가 |
| `data` | CSV/JSON/in-memory data table | 미구현 | 제품 데이터 모델이므로 Application/도메인 모듈로 생성 |
| `chat` | 대화 세션·history | 미구현 | 실제 chat product가 선택될 때 RAG/identity와 조합 |
| `llm` | 모델 호출 | local runtime 생성 완료 | Ollama provider adapter는 실제 소비자 경로가 생길 때 |
| `rag` | 수집·검색·문맥 조합 | local infrastructure profile 완료 | canonical record와 indexing handoff를 소비자 선택 뒤 구현 |
| `search` | keyword/full-text search | Elasticsearch profile 생성 완료 | index schema와 query policy는 소비자 도메인 |
| `vectordb` | embedding/vector retrieval | Qdrant profile 생성 완료 | collection schema와 embedding policy는 소비자 도메인 |
| `storage` | 원본 파일·객체 저장 | local MinIO profile 생성 완료 | bucket policy와 cloud S3 adapter는 소비자 선택 뒤 구현 |
| `signal` | 실시간 시장 신호 | KIS 초기 도메인 slice 완료 | SignalEvent 저장·Outbox, 사용자 shard 구독 제어까지; 전역 구독 projection·fan-out·알림은 소비자 후속 작업 |

`base_server`의 빈 `event` 패키지처럼, 이름만 만든 서비스는 구현 완료로
간주하지 않는다. 표의 “완료”는 명세, 생성 결과, ownership, focused test,
가능하면 독립 Compose 검증까지 갖춘 경우만 의미한다.

## Template 매핑

| Base Server Template | AutoForge에서의 위치 |
| --- | --- |
| `account`, `profile` | identity/session/sharded-profile Blueprint와 소비자 handler |
| `crawler`, `market` | scheduled-ingestion 기반 위의 소비자 domain module |
| `autotrade`, `portfolio` | KIS 전용 주문·포트폴리오 domain module |
| `chat` | RAG, identity, realtime을 선택 조합하는 향후 Blueprint |
| `notification` | notification/realtime 공통 역량의 소비자 조합 |
| `model` | ML/LLM provider와 저장소를 선택하는 향후 Blueprint |
| `admin`, `dashboard`, `tutorial`, `base` | 공통 router/module 조합. 실제 화면·권한은 소비자 소유 |

## 구현 순서

1. **완료된 기반 유지**: FastAPI, PostgreSQL Global/Shard, Redis session,
   RabbitMQ/Outbox, Airflow, Docker/Compose, 로그/metrics envelope.
2. **RAG 공통 인프라**: 완료. `tooling.rag.enabled`가 선택된 경우에만 Qdrant,
   Elasticsearch, Ollama overlay와 비밀 없는 연결 설정을 생성한다. 기본
   Application에는 포함하지 않으며, 모델 다운로드나 외부 credential은 자동 실행하지 않는다.
3. **수집과 저장 조합**: local MinIO S3-compatible profile을 생성할 수 있다.
   소비자가 canonical record/idempotency/storage를
   선택하면 scheduled ingestion과 search/vector indexing handoff를 연결한다.
4. **Realtime/알림**: 검증 가능한 소비자가 생긴 뒤 WebSocket, Redis shared
   state, queue delivery, channel adapter를 하나의 Blueprint로 추가한다.
5. **운영 배포**: PVC/PV, object storage, Ingress/TLS, HPA/PDB, cluster
   topology를 local 계약과 같은 ownership으로 generator/plugin화한다.

## 첫 번째 다음 구현 단위

RAG 전체 기능이나 chat handler를 한 번에 만들지 않는다. 먼저
`RAG infrastructure profile`은 구현·검증되었다. `tooling.rag.enabled`를
선택하면 Qdrant, Elasticsearch, Ollama가 포함된 Compose와 비밀 없는 연결
설정이 생성된다. Qdrant/Elasticsearch는 `rag` profile, 큰 이미지와 모델
공간을 쓰는 Ollama는 `inference` profile에서만 시작한다.

이 단계의 범위는 **실행 기반**까지다. 문서 수집, embedding 생성, 검색 순위,
프롬프트, Bedrock/OpenAI 키, 금융 판단은 소비자 업무 구현이며 다음 단계에서
명시적으로 선택한다.

## 완료 기준

Base Server와 동등한 서비스 범위는 각 행이 “이름 존재”가 아니라 다음을
충족할 때 달성된다.

1. 필요한 Blueprint가 해당 공통 역량을 선택한다.
2. 명세가 실제 생성 결과를 바꾼다.
3. GENERATED/SCAFFOLDED/USER_OWNED 경계가 manifest로 추적된다.
4. 최소 focused test와 독립 runtime 검증이 있다.
5. KIS 같은 소비자가 도메인 코드를 침범하지 않고 그 역량을 사용한다.
