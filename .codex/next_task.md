# 다음 작업

## 현재 목표

문서로 확정한 생성 계약을 코드 모델과 테스트로 옮긴다. 첫 구현은 생성기를 작성하기 전에 입력과 결과 계약을 검증하는 단계다.

## 근거 문서

- `docs/architecture/generation_contract.md`
- `docs/architecture/specification_design.md`
- `docs/architecture/system_design.md`

## 다음 구현 범위

1. ProjectSpec과 ModuleSpec Pydantic 모델
2. 첫 MVP 공통 Type System
3. 이름과 경로 검증
4. 파일 소유권 Enum
   - GENERATED
   - SCAFFOLDED
   - USER_OWNED
5. GenerationPlan과 파일 계획 항목 모델
6. GenerationManifest와 파일 결과 모델
7. 명세 버전 및 Hash 계산 계약
8. 위 모델의 pytest 테스트

## 이번 범위에서 구현하지 않음

- 실제 파일 Generator
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