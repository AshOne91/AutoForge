# AutoForge

AutoForge는 YAML 명세를 읽어, 반복 가능한 기본 구조를 갖춘 **FastAPI 서버 프로젝트**를
생성하는 Python 도구다.

로그인 서버를 만들 때마다 폴더, Docker, PostgreSQL, Redis, 테스트의 기본 틀을 손으로
복사하지 않도록 돕는다. AutoForge가 공통 뼈대를 만들고, 개발자는 `SCAFFOLDED`로 표시된
handler에 실제 서비스 규칙을 작성한다.

```text
프로젝트 명세
  → 웹서버 생성
  → 테스트·빌드 검증
  → 개발자가 도메인 코드 작성
  → Docker에서 서비스 조합 실행
```

이 문서는 프로젝트 입구다. 현재 구현 범위와 다음 작업을 여기서 따로 정의하지 않는다.
각각 [현재 상태](.codex/current_status.md)와 [다음 작업](.codex/next_task.md)을 확인한다.

## 참고 프로젝트

- `common-tool`: 명령과 설정 기반 코드 생성
- `gameserver`: Application, 도메인 Template, Service, Tool 책임 분리
- `base_server`: 생성될 FastAPI 서버의 기준 구조

AutoForge는 참고 프로젝트의 포팅이 아니라 재설계 프로젝트다.

## 처음 온 개발자는 이 순서만 따르면 됩니다

이 저장소를 처음 받았다면 아래 세 문서를 **순서대로** 읽고 명령을 실행한다. Windows,
Conda, Docker를 전혀 설치하지 않은 PC도 두 번째 문서부터 시작할 수 있다.

1. 이 `README.md` — 프로젝트가 무엇을 만드는지만 짧게 확인한다.
2. [처음부터 만드는 AutoForge 로그인 서버](docs/guides/login_server_from_zero.md) — Conda와
   Docker 설치부터 명세 작성, 서버 생성, 로그인·Redis 세션 테스트까지 따라 한다.
3. [AutoForge Quest: 퀘스트 보드 서버 만들기](docs/guides/domain_service_workbook.md) — 로그인
   서버 위에 DB/SQL, RabbitMQ, 캐시, MinIO, 검색·RAG, 알림, ELK, 단일 PC HA를 필요한
   순서로 추가한다.

두 실습을 끝낼 때까지 `docs/architecture/`를 모두 읽을 필요는 없다. “왜 이렇게
동작하지?”라는 질문이 생긴 부분만 각 Guide의 정본 문서 링크를 따라간다.

## AutoForge가 하는 일과 하지 않는 일

AutoForge는 FastAPI 모듈, Docker Compose 환경, SQL/Alembic 기반 DB 구조, 그리고
선택 서비스(RabbitMQ, Airflow, MinIO, 검색·벡터 DB, 관측성, 단일 호스트 HA)의 공통
구성을 명세에서 생성하고 검증한다.

특정 서비스의 업무 규칙은 자동으로 정하지 않는다. 예를 들어 “누가 주식을 주문할 수
있는가”, “로그인에 어떤 추가 인증을 요구하는가”는 생성 후 handler와 도메인 테스트에서
개발자가 결정한다.

```text
YAML 명세
  → AutoForge 생성·검증
  → 생성된 FastAPI 프로젝트
  → 개발자가 도메인 handler·테스트 작성
  → Docker에서 서비스 조합 실행
```

`GENERATED` 파일은 명세를 고쳐 다시 생성할 수 있고, `SCAFFOLDED` 파일은 개발자가
작성하며 AutoForge가 보존한다. 자세한 소유권은
[생성·소유권 계약](docs/architecture/generation_contract.md)이 설명한다.

## 더 깊게 볼 문서

- [전체 시스템 구조](docs/architecture/system_design.md)
- [명세 설계](docs/architecture/specification_design.md)
- [DB 생성](docs/architecture/database_generation.md)
- [Plugin System](docs/architecture/plugin_system.md)
- [EventBus·Pipeline](docs/architecture/event_driven_architecture.md)
