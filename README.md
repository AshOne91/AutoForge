# AutoForge

AutoForge는 ProjectSpec을 기반으로 모듈형 FastAPI 웹서버 프로젝트를 생성하는 Python 도구다.

```text
프로젝트 명세
  → 웹서버 생성
  → 테스트 및 빌드
  → 검증된 변경 Commit
  → 작업 브랜치 Push
  → Pull Request 생성
```

현재 개발 초점은 로컬 프로젝트 생성이다. GitHub Webhook, Git 반영, AI 보조 생성은 후속 단계에서 구현한다.

## 참고 프로젝트

- `common-tool`: 명령과 설정 기반 코드 생성
- `gameserver`: Application, 도메인 Template, Service, Tool 책임 분리
- `base_server`: 생성될 FastAPI 서버의 기준 구조

AutoForge는 참고 프로젝트의 포팅이 아니라 재설계 프로젝트다.

## 현재 상태

- Python 3.12
- Typer CLI 기본 구조
- 설정, Registry, EventBus, Task, PluginManager 기반
- 기존 테스트의 pytest 마이그레이션 완료
- ProjectSpec과 ModuleSpec 검증 모델
- 공통 Type System
- GenerationPlan과 GenerationManifest 계약
- Workspace 경로 안전 경계
- 최소 FastAPI Project 메모리 렌더링과 Dry-run
- Workspace 상태 기반 충돌 판정
- 안전한 Workspace 적용과 GenerationManifest 생성
- Manifest의 결정적 JSON 저장과 검증된 로딩
- 생성 프로젝트 Import와 pytest 검증
- Pydantic Model 및 Request/Response Schema 생성
- FastAPI Router와 사용자 보존 Handler Scaffold 생성
- Manifest 기반 GENERATED 파일 안전 교체
- Endpoint 추가 재생성 시 Handler 보존
- Application Module Registry와 Tutorial Endpoint 연결
- GenerationJob과 복수 Manifest 집계 계약
- Generator/Validator Plugin Registry와 Built-in Plugin Catalog
- 전체 테스트 224개 통과 기준선

다음 단계는 DatabaseSpec과 Repository 계약의 최소 경계 설계다.

## 첫 번째 MVP

1. 로컬 YAML ProjectSpec을 읽는다.
2. 프로젝트와 패키지 이름을 검증한다.
3. 결정적인 생성 계획을 미리 보여준다.
4. 격리된 Workspace에 최소 FastAPI 프로젝트를 생성한다.
5. 생성 파일 Manifest를 기록한다.
6. 생성 프로젝트의 테스트와 패키지 검증을 실행한다.

## 문서

- [처음부터 만드는 AutoForge 로그인 서버](docs/guides/login_server_from_zero.md):
  도구가 없는 Windows PC에서 시작해 명세, 생성, Docker, 로그인, Redis 세션,
  ping/pong, 테스트까지 진행하는 초보자용 실습 GUIDE
- `docs/architecture/system_design.md`
- `docs/architecture/generation_contract.md`
- `docs/architecture/specification_design.md`
- `docs/architecture/plugin_system.md`
- `docs/architecture/event_driven_architecture.md`
- `.codex/project_context.md`
- `.codex/roadmap.md`
