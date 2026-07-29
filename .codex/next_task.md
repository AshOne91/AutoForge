# 다음 작업

전체 배경과 현재 구조는 `docs/PROJECT_GUIDE_2026-07-29.md`를 먼저 읽는다.

## 현재 목표

충돌 판정이 끝난 GenerationPlan과 렌더링 결과를 Workspace에 안전하게
적용하고 GenerationManifest를 만든다. 충돌이 하나라도 있으면 쓰기 전에
전체 적용을 중단한다.

## 근거 문서

- `docs/architecture/generation_contract.md`
- `docs/architecture/specification_design.md`
- `docs/architecture/system_design.md`

## 다음 구현 범위

1. 계획과 렌더링 결과의 경로 및 Hash 일치 검증
2. CONFLICT가 있으면 파일 쓰기 전 전체 중단
3. CREATE 파일의 부모 디렉터리 생성과 UTF-8 쓰기
4. KEEP과 SKIP 파일 보존
5. 파일별 결과를 GenerationManifest로 변환
6. 생성된 최소 FastAPI 프로젝트의 pytest 실행 준비

## 이번 범위에서 구현하지 않음

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
Webhook 단계에 진입할 때 `.codex/roadmap.md`의 해당 체크 항목에 따라 소스와
테스트 디렉터리를 구현 파일과 함께 다시 생성한다.
