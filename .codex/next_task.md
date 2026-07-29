# 다음 작업

## 현재 목표

검증된 ProjectSpec을 결정적인 GenerationPlan으로 변환하는 첫 번째 최소
FastAPI Project Generator를 구현한다. 먼저 실제 파일을 쓰지 않는 계획
생성으로 출력 구조와 소유권 계약을 검증한다.

## 근거 문서

- `docs/architecture/generation_contract.md`
- `docs/architecture/specification_design.md`
- `docs/architecture/system_design.md`

## 다음 구현 범위

1. Generator의 최소 입력과 출력 Protocol 정의
2. 최소 FastAPI 프로젝트 파일 목록 정의
3. ProjectSpec에서 GenerationPlan 생성
4. 생성 내용의 결정적 Hash 계산
5. 같은 명세가 같은 계획을 만드는지 pytest 검증
6. 실제 파일 적용 전 Dry-run 결과 검증

## 이번 범위에서 구현하지 않음

- 실제 Workspace 파일 쓰기
- Template 렌더링
- Tutorial Module Generator
- PluginLoader
- Webhook
- Git Commit, Push, Pull Request
- CI/CD 실행
- Database Generator
- AI 생성

## 유지할 최종 아키텍처

- Plugin은 Generator, Validator, Builder, Git, CI/CD 기능을 확장한다.
- Plugin Metadata는 호환성, Capability, 의존성, 권한을 표현한다.
- EventBus는 실행 사건을 전달한다.
- Pipeline은 실행 순서와 실패 정책을 제어한다.
- Manifest는 생성 파일의 소유권과 출처를 추적한다.

구체적인 코드 파일과 테스트 계획을 먼저 제시하고 사용자 승인을 받은 후에만 구현한다.

현재 비어 있는 미래 기능 디렉터리는 제거된 상태다. Plugin, Database, Git,
Webhook 단계에 진입할 때 `.codex/ROADMAP.md`의 해당 체크 항목에 따라 소스와
테스트 디렉터리를 구현 파일과 함께 다시 생성한다.
