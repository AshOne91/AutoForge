# 다음 작업

전체 배경과 현재 구조는 `docs/PROJECT_GUIDE_2026-07-29.md`를 먼저 읽는다.

## 현재 목표

Validator Plugin을 async typed Registry에 등록하고 현재 ProjectValidator를
Metadata와 함께 조회·실행할 수 있게 한다.

## 근거 문서

- `docs/architecture/generation_contract.md`
- `docs/architecture/specification_design.md`
- `docs/architecture/system_design.md`

## 다음 구현 범위

1. Generator typed Registry에서 검증된 패턴 재사용
2. 범용 PluginManager의 execute 계약은 변경하지 않음
3. Validator ID·버전과 async 실행 계약 정의
4. ProjectValidator Adapter와 Metadata 구성
5. 중복 Validator ID와 Metadata 불일치 거부
6. Import·pytest·Ruff·Build 검증 회귀 테스트
7. PluginLoader와 기존 PluginManager 회귀 테스트

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
