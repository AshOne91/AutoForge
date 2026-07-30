# 다음 작업

전체 배경과 현재 구조는 `docs/PROJECT_GUIDE_2026-07-29.md`를 먼저 읽는다.

## 현재 목표

Plugin Metadata의 API 호환성, 의존성과 권한 정책을 작은 범위로 확정한다.

## 근거 문서

- `docs/architecture/generation_contract.md`
- `docs/architecture/specification_design.md`
- `docs/architecture/system_design.md`

## 다음 구현 범위

1. 현재 Plugin API 버전과 호환 범위 정의
2. 의존 Plugin ID와 버전 요구사항의 최소 표현 정의
3. 파일, Process, Network 등 권한과 실행 Capability 분리
4. 자기 의존, 중복 의존성과 중복 권한 거부
5. 지원하지 않는 API 버전 거부
6. 기존 Generator Plugin과 PluginManager 회귀 테스트

## 이번 범위에서 구현하지 않음

- Template 렌더링
- GenerationJob 실행기
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
Webhook 단계에 진입할 때 `.codex/roadmap.md`의 해당 체크 항목에 따라 소스와
테스트 디렉터리를 구현 파일과 함께 다시 생성한다.
