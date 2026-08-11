# Services

명세를 생성 계획과 검증 결과로 변환하는 Application Service 구현 계층이다.

- `generation`: Project/Module/DB/환경 산출물 생성과 Plan 적용
- `validation`: 생성 프로젝트의 import, pytest, Ruff와 build 검증

Git, Webhook과 외부 Process 구현은 Infrastructure 계층이 소유한다. 전체 계층
경계는 [`system_design.md`](../../../docs/architecture/system_design.md)를 따른다.
