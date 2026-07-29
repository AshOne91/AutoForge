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

- [ ] 최소 FastAPI Project Generator
- [ ] Tutorial Module Generator
- [ ] Pydantic Model 및 Request/Response Generator
- [ ] Router Generator
- [ ] Handler Scaffold Generator
- [ ] Application Module Registry Generator
- [ ] 생성 테스트와 사용자 코드 보존 테스트

## 3단계 - Workspace와 검증 Pipeline

- [x] Workspace 경로 안전 경계
- [ ] 격리된 Workspace 생성과 수명주기
- [ ] Dry-run과 충돌 탐지
- [ ] 결정적 반복 생성
- [ ] Import 및 pytest Validator
- [ ] lint와 Package Build Validator
- [ ] 구조화된 Job 결과

## 4단계 - Plugin 확장 구조

- [ ] Generator 계약을 Plugin API로 확정
- [ ] Plugin Metadata와 Capability 검증
- [ ] PluginLoader 구현
- [ ] Generator 및 Validator Plugin 등록
- [ ] Plugin 의존성과 권한 정책
- [ ] `plugins/` 구현 및 테스트 디렉터리 생성

## 5단계 - 데이터 및 서비스 생성

- [ ] DatabaseSpec과 Repository 계약
- [ ] SQLAlchemy 및 Alembic Plugin
- [ ] DB별 DDL Plugin
- [ ] Cache, Queue, WebSocket Service Blueprint
- [ ] CSV Data Table Generator
- [ ] `infrastructure/database/` 구현 디렉터리 생성

## 6단계 - Event와 자동화 Pipeline

- [ ] Job 및 Generation Event 정의
- [ ] Logging, Audit, Metrics Handler
- [ ] Generation Pipeline
- [ ] Validation 및 Build Pipeline
- [ ] 실패·재시도·Timeout 정책

## 7단계 - Git 자동화

- [ ] 저장소 Checkout Workspace
- [ ] 작업 브랜치 생성
- [ ] 검증된 변경만 Commit
- [ ] Push와 Pull Request
- [ ] Git Provider Plugin
- [ ] `infrastructure/git/` 구현 디렉터리 생성

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
