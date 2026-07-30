# 현재 상태

## 완료

- 설정 로딩 기본 구조
- Registry 안정화
- Plugin 기반 클래스와 Metadata
- PluginManager 안정화
- Event와 비동기 EventBus 기본 구조
- Task와 TaskManager 기본 구조
- 기존 테스트의 pytest 마이그레이션
- ProjectSpec과 ModuleSpec 검증 모델
- 첫 MVP 공통 Type System
- GenerationPlan과 GenerationManifest 모델
- 명세와 파일 내용 Hash 계산
- Workspace 상대경로 검증과 경로 이탈 방지
- 제네릭 Generator Protocol
- 최소 FastAPI Project Generator 렌더링과 Dry-run
- Workspace 상태 기반 생성 계획 충돌 판정
- GenerationPlan의 안전한 Workspace 적용과 메모리 Manifest 생성
- GenerationManifest의 결정적 JSON 저장과 검증된 로딩
- 비동기 외부 프로세스 실행과 Timeout 처리
- 생성 프로젝트 Import 및 pytest 검증
- 공통 Type의 Python/Pydantic Type 변환
- ModuleSpec 기반 Pydantic Model 및 Request/Response Schema 생성
- ModuleSpec 기반 FastAPI Router와 Handler Scaffold 생성
- 동일 명세 재실행 시 사용자 Handler 보존
- Manifest 기반 GENERATED 파일 안전 교체
- Endpoint 추가 재생성 시 Router 갱신과 Handler 보존
- Application Module Registry 생성
- Project와 Tutorial Module 조합 및 실제 Endpoint 검증
- GenerationJob과 Project/Module Unit 집계 모델
- 복수 Manifest의 Job ID, Specification과 파일 경로 중복 검증
- 버전형 GenerationJobManifest의 결정적 JSON 저장과 검증된 로딩
- 기존 GenerationManifest JSON 로딩 호환성
- 명시적 Config 주입과 전역 Config 제거
- 프로젝트 디렉터리 밖에서 동작하는 version CLI
- 미구현 CLI의 명확한 실패 상태
- 전체 테스트 154개 통과 기준선

## 진행 중

- 문서 정합성 정리
- 패키지와 코딩 스타일 정리
- lint와 Package Build Validator 준비

## 존재하지만 미완성

- CLI 명령
- Plugin Framework
- Pipeline 추상화
PluginLoader는 구현 예정 모듈이며 아직 공개 API가 없다. Pipeline은 추상
클래스 자리표시자뿐이므로 Plugin Framework는 아직 완성으로 보지 않는다.

## 시작하지 않음

- GenerationJob 실행 조정 Service
- lint와 Package Build 검증
- Build 및 Git 서비스
- Webhook 서비스
- AI 생성

## 현재 제약

로컬 생성과 검증이 안정되기 전에 Webhook, Git 자동화, AI를 구현하지 않는다. 동작하는 Generator로 확장 계약을 확인하기 전에는 PluginLoader를 구현하지 않는다.

미래 단계용 빈 디렉터리는 미리 유지하지 않는다. 각 단계에 진입할 때
Roadmap과 다음 작업 문서를 확인하고 필요한 패키지와 테스트 디렉터리를
구현과 함께 생성한다.

전체 인수인계 문서는 `docs/PROJECT_GUIDE_2026-07-29.md`를 참고한다.
