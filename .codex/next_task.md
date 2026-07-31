# 다음 작업

전체 배경과 현재 구조는 `docs/PROJECT_GUIDE_2026-07-29.md`를 먼저 읽는다.

## 현재 목표

DatabaseSpec과 Repository 최소 명세 계약은 구현되었고
`C:\kis-auto-trading\specifications\account.yaml`로 검증되었다.

다음 목표는 기술 중립 Repository Protocol과 테스트용 Fake Repository를
GenerationPlan으로 만드는 최소 Generator를 설계하는 것이다. 생성 파일의
소유권과 반복 생성 안전 정책은 기존 Generation Contract를 그대로 사용한다.

## 근거 문서

- `docs/architecture/generation_contract.md`
- `docs/architecture/specification_design.md`
- `docs/architecture/system_design.md`

## 다음 구현 범위

1. Repository Protocol과 Fake Repository의 생성 경로 및 소유권 확정
2. Repository operation을 Python Protocol method로 변환하는 최소 규칙 확정
3. `UserProfileRepository` 생성 결과와 type hint 검증
4. 기존 Module Generator와 별도 Generator로 유지할지 조합 경계 확인
5. kis-auto-trading Account/Profile 명세의 dry-run GenerationPlan 검증
6. 구현 전 구체적인 코드·테스트 파일 계획 제시

## 이번 범위에서 구현하지 않음

- Database 구현 코드
- SQLAlchemy 및 Alembic Plugin
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
