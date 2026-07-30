# 다음 작업

전체 배경과 현재 구조는 `docs/PROJECT_GUIDE_2026-07-29.md`를 먼저 읽는다.

## 현재 목표

Plugin Manifest에 명시적인 Entrypoint 계약을 추가하고, 발견과 분리된
신뢰된 로딩 API로 PluginManager에 등록한다.

## 근거 문서

- `docs/architecture/generation_contract.md`
- `docs/architecture/specification_design.md`
- `docs/architecture/system_design.md`

## 다음 구현 범위

1. `module:factory` 형식의 Entrypoint 문법과 검증 정의
2. 발견 API는 계속 코드를 실행하지 않음
3. 명시적 trusted 로딩 API에서만 Import와 Factory 호출
4. 반환 객체의 Plugin 계약과 Metadata 일치 검증
5. 의존성 순서에 따른 PluginManager 등록
6. 중간 실패 시 부분 등록 방지 또는 명확한 Rollback
7. 기존 발견·Generator Plugin·PluginManager 회귀 테스트

## 이번 범위에서 구현하지 않음

- Template 렌더링
- GenerationJob 실행기
- 권한의 OS 수준 Sandbox 강제
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
Webhook 단계에 진입할 때 `.codex/roadmap.md`의 해당 체크 항목에 따라 소스와
테스트 디렉터리를 구현 파일과 함께 다시 생성한다.
