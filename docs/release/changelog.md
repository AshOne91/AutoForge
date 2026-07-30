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
- 계획과 렌더링 결과를 재검증한 뒤 Workspace에 적용하는 서비스를 추가했다.
- 충돌 시 쓰기 전 전체 중단하고 CREATE, KEEP, SKIP 결과 Manifest를 생성한다.
- 생성 파일을 플랫폼과 무관한 UTF-8 바이트로 기록해 Hash 결정성을 보장한다.
- GenerationManifest를 `.autoforge/manifest.json`에 결정적으로 저장하고
  Pydantic 모델로 검증해 로딩하는 저장소를 추가했다.
- shell을 사용하지 않는 비동기 외부 프로세스 실행과 Timeout 처리를 추가했다.
- 생성된 FastAPI 프로젝트의 Import와 pytest를 실제 별도 프로세스로 검증한다.
- Starlette 1.3.1 TestClient 요구사항에 맞춰 테스트 의존성을 `httpx2`로
  명시했다.
- 공통 FieldType을 Python 3.12 타입 표현으로 변환하는 Renderer를 추가했다.
- ModuleSpec에서 Pydantic Model과 Endpoint Request/Response Schema를
  결정적으로 생성한다.
- ModuleSpec에서 FastAPI Router와 비동기 Handler Scaffold를 생성한다.
- Handler는 SCAFFOLDED 소유권으로 분리해 동일 명세 재실행에서 사용자 수정을
  보존한다.
- 이전 Manifest와 현재 파일 Hash가 일치하는 GENERATED 파일만 안전하게
  교체하고 CHANGED 결과를 기록한다.
- Endpoint 추가 재생성에서 Router를 갱신하면서 사용자 Handler를 보존한다.
