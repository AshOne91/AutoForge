# AutoForge 로드맵

## 0단계 - 안정화 및 방향 정렬

- [x] pytest 수집 오류 수정
- [x] Registry 안정화
- [x] PluginManager 안정화
- [x] 전체 테스트 통과 기준선 확보
- [x] 참고 프로젝트 기반 제품 목표와 문서 정렬

## 1단계 - 생성 계약과 명세

- [x] 생성 파일 소유권 정의
- [x] 안전한 반복 생성 원칙 정의
- [x] Project, Application, Module 명세 구조 설계
- [x] API/Packet, Model, DB Schema 확장 방향 설계
- [x] ProjectSpec과 ModuleSpec 코드 모델 구현
- [x] 공통 Type System 구현
- [x] GenerationPlan과 Manifest 모델 구현
- [x] 이름, 경로, 명세 버전 검증 구현

## 2단계 - 첫 번째 수직 Generator

- [x] 최소 FastAPI Project Generator 렌더링과 Dry-run
- [x] 최소 FastAPI Project Generator Workspace 적용
- [x] Tutorial Module Generator
- [x] Pydantic Model 및 Request/Response Generator
- [x] Router Generator
- [x] Handler Scaffold Generator
- [x] Application Module Registry Generator
- [x] 생성 테스트와 사용자 코드 보존 테스트

## 3단계 - Workspace와 검증 Pipeline

- [x] Workspace 경로 안전 경계
- [x] 격리된 Workspace 생성과 수명주기
- [x] Dry-run과 충돌 탐지
- [x] 결정적 CREATE와 KEEP/SKIP 보존
- [x] Import 및 pytest Validator
- [x] lint와 Package Build Validator
- [x] 구조화된 Job 결과 계약

## 4단계 - Plugin 확장 구조

- [x] Generator 계약을 Plugin API로 확정
- [x] Plugin Metadata와 Capability 검증
- [x] PluginLoader 구현
- [x] Generator 및 Validator Plugin 등록
- [x] Plugin 의존성과 권한 정책
- [x] `plugins/` Built-in Catalog 구현 및 테스트 디렉터리 생성

## 5단계 - 데이터 및 서비스 생성

- [x] DatabaseSpec과 Repository 최소 명세 계약
- [x] 참고 프로젝트 기반 Database 생성 책임과 경계 문서화
- [x] kis-auto-trading Account/Profile 명세로 계약 검증
- [x] Repository Protocol과 Fake Repository Generator
- [x] SQLAlchemy 및 Alembic Plugin
  - [x] SQLAlchemy async Base, Session과 ShardRouter Generator
  - [x] SQLAlchemy 2.x Record Model Generator
  - [x] Repository Adapter와 Domain/Record 변환 Generator
  - [x] Store별 Alembic 실행 환경과 최초 baseline revision Generator
- [x] PostgreSQL Global/Shard DDL Plugin
- [ ] MySQL을 포함한 추가 DB Provider Plugin(PostgreSQL 안정화 이후)
- [ ] 필수 Redis Service Blueprint와 Adapter
  - [x] Standalone 연결과 공통 SessionStore 계약
  - [x] Sentinel 연결 공급자와 Primary 자동 장애 전환 검증
  - [x] Cluster-aware 연결, 3 Primary+3 Replica 장애 전환과 hash-tag 키 규칙
  - [ ] AWS ElastiCache Multi-AZ/Cluster Mode 배포 설정 계약
- [x] 필수 RabbitMQ Transport와 Worker Blueprint
- [x] Transactional Outbox Relay
- [ ] WebSocket 및 추가 Service Blueprint
- [ ] CSV Data Table Generator
- [ ] `infrastructure/database/` 구현 디렉터리 생성

## 6단계 - Event와 자동화 Pipeline

- [x] EventBus, Handler, Pipeline 및 외부 Transport 책임 경계 설계
- [x] 불변 Event metadata와 typed Handler 계약
- [x] 순차 Pipeline 실행, task timeout·retry·실패·취소 정책
- [x] Pipeline과 Task lifecycle Event 발행
- [x] Job 및 Generation Event 정의
- [x] GenerationJob 상태 머신과 async JobStore Protocol
- [x] PostgreSQL JobStore와 원자적 idempotent claim
- [x] 인증된 idempotent trigger/status API와 입력 경계
- [x] 실행 lease, heartbeat, stale-worker fencing과 abandoned Job 복구
- [x] lease worker와 Generation Pipeline 연결
- [x] worker polling loop, abandoned sweep와 graceful shutdown 운영 adapter
- [x] Logging과 Audit Handler 및 구독 실패 정책
- [x] PostgreSQL AuditSink와 event_id 중복 방지
- [ ] Metrics Handler
- [x] Generation Pipeline
- [x] Validation 및 Build Pipeline
- [x] 실패·재시도·Timeout 정책

## 7단계 - Git 자동화

- [x] 안전한 Git Provider checkout 계약과 adapter
- [x] repository submission과 Job별 IsolatedWorkspace checkout 연결
- [x] expected base와 변경 allowlist 기반 안전한 branch/commit adapter
- [x] 작업 브랜치 생성
- [x] 검증된 변경만 Commit
- [x] Secret 참조와 non-force push adapter 기반
- [x] Push와 Pull Request
- [ ] Git Provider Plugin
- [x] `infrastructure/git/` 구현 디렉터리 생성

## 8단계 - Webhook과 CI/CD

- [ ] GitHub Webhook 서명 검증
- [ ] 이벤트 정규화와 중복 방지
- [ ] HTTP 요청과 분리된 Job 실행
- [ ] GitHub Actions 및 Jenkins 설정 Generator
- [ ] Docker Build, Artifact, Deployment Plugin
- [ ] `infrastructure/webhook/` 구현 디렉터리 생성

## 9단계 - 향후 기능

- [ ] AI 명세 작성 보조
- [ ] AI 코드 생성 보조
- [ ] Dashboard와 분산 작업자
- [ ] Plugin 마켓플레이스

Plugin, Metadata, EventBus, Pipeline, Git 및 CI/CD는 AutoForge 최종 구조의 핵심이다. 단계 구분은 비전을 축소하기 위한 것이 아니라 각 계약을 실제 Generator로 검증하기 위한 구현 순서다.

빈 디렉터리는 구조를 미리 보이기 위한 용도로 유지하지 않는다. 각 단계의
구현을 시작할 때 필요한 소스와 테스트 디렉터리를 파일과 함께 생성한다.
> Status update (2026-08-07): the non-force Push adapter and its GenerationJob
> `pushing` lifecycle integration are complete. In the combined "Push and Pull
> Request" item below, only Pull Request automation remains incomplete.
