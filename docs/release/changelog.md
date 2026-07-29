# Changelog

## Unreleased

- Registry와 PluginManager API 사용을 안정화했다.
- 기존 테스트를 pytest 테스트 함수로 정리했다.
- ProjectSpec, ModuleSpec과 공통 Type System을 추가했다.
- GenerationPlan, GenerationManifest와 Hash 계약을 추가했다.
- Workspace 경로 안전 경계를 추가했다.
- 중복되고 사용되지 않는 Sample Plugin 골격을 제거했다.
- 최소 FastAPI Project 렌더링과 Dry-run을 추가했다.
- Workspace 상태 기반 GenerationPlan 충돌 판정을 추가했다.
- import 시 설정을 읽던 전역 Config를 제거했다.
- 프로젝트 디렉터리 밖에서도 version CLI가 동작하도록 수정했다.
- 미구현 CLI 명령이 성공처럼 종료되지 않도록 수정했다.
- 2026-07-29 기준 통합 프로젝트 가이드를 추가했다.
