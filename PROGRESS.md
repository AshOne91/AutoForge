# 문서 검증 및 환경 구축 진행 상황 (PROGRESS.md)

> Purpose: live work log for the clean-computer, junior-developer walkthrough.
> This is a verification ledger, not an architecture or operational-status source
> of truth. The only walkthrough instructions are, in order: `README.md`,
> `docs/guides/login_server_from_zero.md`, and
> `docs/guides/domain_service_workbook.md`.

## 📌 Current State

- **현재 진행 중인 파일**: `docs/guides/domain_service_workbook.md`
- **현재 진행 단계/Level**: 세 문서 Fresh-PC walkthrough 완료
- **전체 진행률**: 100% (문서별 실제 실행 검증, 발견 사항 보완, 최종 Markdown 검증 완료)

> 아래 1~40번은 이전 시도의 이력이다. 이번 재실행에서는 증거로 사용하지 않으며,
> README부터 모든 명령과 검증을 다시 수행한 뒤 새 항목으로 기록한다.

## Rules for this run

- Follow the three documents in their stated order.
- Record each attempted step and its result before beginning the next step.
- When a documented step fails, stop the walkthrough, record the evidence, fix
  the relevant guide, then retry that same step.

## 📝 Execution & Fix Log

### 이전 시도 이력 (이번 재실행의 증거 아님)

| Step | Document | Action | Result | Evidence / next action |
| --- | --- | --- | --- | --- |
| 1 | `README.md` | Read the project entry document. | PASS | It identifies AutoForge as the generator and links to the two beginner walkthroughs. Next: follow the login-server guide from its prerequisite/environment section. |
| 2 | `login_server_from_zero.md` §2 | Run the four documented prerequisite checks: Git, Conda, Docker client/server, and `hello-world`. | PASS | Git 2.51.0, Conda 25.9.1, Docker 29.1.2, and `hello-world` all succeeded. Existing tools are present in this verification environment; continue with the guide's fresh clone/environment commands. |
| 3 | Fresh-project reset | Remove only prior login-server runtime data, external clone, generated login folders, and the `autoforge` Conda environment before replaying the guide. | PARTIAL | Login Compose containers, its network, the external clone, the spec folder, and Conda environment were removed. `C:\workspace\login-server` could not be removed because the cleanup shell itself used that folder as its working directory; retry that exact deletion from `C:\AutoForge`. This is an execution-context issue, not a guide defect. |
| 4 | Fresh-project reset | Remove the remaining generated login-server folder from a neutral working directory and recheck the reset targets. | PASS | `C:\src\AutoForge`, both login-server folders, and the `autoforge` Conda environment are absent. The walkthrough can now replay the guide's project setup from a clean project state. |
| 5 | `login_server_from_zero.md` §4 | Clone AutoForge, create `autoforge` with Python 3.12, activate it, upgrade pip, and install `.[test,server]`. | PASS | Fresh clone completed at `C:\src\AutoForge`; `conda activate autoforge` selected Python 3.12.13; editable installation and test/server extras completed. Next: run the documented CLI and core specification test. |
| 6 | `login_server_from_zero.md` §4 | Run `python -m autoforge.main version` and the focused specification test. | PASS | CLI reported `AutoForge v0.1.0`; `tests/core/test_specification_models.py` passed (55 tests). Next: create the three login-server specification files exactly as documented. |
| 7 | `login_server_from_zero.md` §5 | Create `autoforge.yaml`, `identity.yaml`, and `system.yaml` in the documented separate specification folder. | PASS | The YAML files were created exactly under `C:\workspace\login-server-spec`. Next: run AutoForge generation without manually creating any output files. |
| 8 | `login_server_from_zero.md` §6 | Generate the login server from the YAML project and module specifications. | PASS | AutoForge generated and validated 3 units in `C:\workspace\login-server` (`job_id=de0e3aab-a6b1-4972-b82c-2407690f4b7c`). Next: create the local `.env` from its generated example and validate ports. |
| 9 | `login_server_from_zero.md` §8 | Copy `environment/.env.example` to `.env` and run the preflight port validation. | PASS | The generated local environment file was created and `validate-ports` accepted its two host-port overrides. Next: implement the first scaffolded `ping` handler and its focused test. |
| 10 | `login_server_from_zero.md` §9 | Replace the scaffolded `ping` placeholder with `pong`, add the documented async test, and run it. | PASS | `tests/test_system_ping.py` passed (1 test). Next: start the generated Compose stack and check `/health` and `/api/system/ping`. |
| 11 | `login_server_from_zero.md` §10 | Build and start the generated PostgreSQL, Redis, migration, and FastAPI Compose services; call health and ping endpoints. | PASS | Compose reported healthy application/PostgreSQL/Redis services; `/health` returned `{"status":"ok"}` and `/api/system/ping` returned `{"message":"pong"}`. Next: add the documented password helper and focused test. |
| 12 | `login_server_from_zero.md` §11 | Add the documented PBKDF2 password helper and run its focused test. | PASS | `tests/test_passwords.py` passed (1 test); the original password verifies and a different password is rejected. Next: replace the identity handler placeholders with the documented signup/login/session implementation. |
| 13 | `login_server_from_zero.md` §12 | Apply the documented identity handler implementation. | RETRY | The first file-replacement patch used an unsupported same-file delete/add form and made no file change. Retry with one in-place update; this is a tooling syntax issue, not a guide defect. |
| 14 | `login_server_from_zero.md` §12-13 | Implement signup/login/session handlers, rebuild, then verify signup, duplicate 409, login, Redis session validation, and validation after application restart. | PASS | Focused generated-server tests passed (2 tests). The HTTP flow completed and all four returned user IDs matched before and after application restart. The login-server walkthrough is complete with no guide defect found. Next: read and follow the Quest workbook from Level 1. |
| 15 | Quest workbook Level 1 reset | Remove a prior profile-server validation output before following the documented `Copy-Item` step. | RETRY | The generated folders were removed, but the cleanup command was run from the wrong directory so Compose could not read its `.env`; profile containers may remain. Remove those known prior containers explicitly, then restart Level 1. This is an execution-context issue, not a guide defect. |
| 16 | Quest workbook Level 1 reset | Remove the known prior profile-server containers, volumes, and network by their Compose project label. | PASS | No prior profile-server generated folders remain; its previous Compose runtime resources were removed. Next: copy the completed login specification folder and apply the documented profile YAML changes. |
| 17 | `domain_service_workbook.md` Level 1 §4.1-4.3 | Copy the login specification, add the profile module/DB/idempotency YAML, generate a separate server, and inspect its generated DB artifacts. | PASS | AutoForge generated and validated 4 units. All documented profile artifacts exist; both raw SQL and the scaffolded Alembic baseline create `user_profiles`. Next: create the generated profile `.env`, validate ports, and repeat the completed login implementation with the `profile_server` package prefix. |
| 18 | `domain_service_workbook.md` Level 1 §4.4-4.6 | Configure the profile environment, repeat the documented login scaffolds with the new package prefix, implement the profile handler, and run the full HTTP exercise. | PASS | Port validation and 2 focused tests passed. Compose health passed; signup/login/profile update/replay/read all returned the same user, replay reused its timestamp, and a reused key with different body returned 409. Level 1 is complete. Next: follow Level 2's one-service expansion YAML and shared execution loop. |
| 19 | `domain_service_workbook.md` Level 2 | Merge the RabbitMQ/Durable Job YAML into the profile specification and generate. | RETRY | I accidentally created a second `application.services` key instead of adding `events` to the existing list; YAML retained only the later key and generation correctly rejected missing `redis_session`. The guide explicitly warns against duplicate top-level/same-location keys, so this is a walkthrough transcription error, not a guide defect. Merge the two services into one list and retry. |
| 20 | `domain_service_workbook.md` Level 2 | Regenerate with the corrected merged service list. | BLOCKED | Generation reached project validation but failed at Ruff. This is an AutoForge-generated-output failure, not a YAML or guide failure. Next: run the exact generated-project Ruff command, repair the responsible AutoForge generator, then rerun this same Level 2 step. |
| 21 | `domain_service_workbook.md` Level 2 shared execution loop | Regenerate with the repaired AutoForge clone, add all newly generated environment values, validate ports, and start the full Compose stack. | BLOCKED | Generation and port validation now pass; RabbitMQ, application, relay, message worker, and durable-job worker are healthy. `airflow-init` exits 1, so the documented Level 2 completion condition is not met. Next: inspect only the `airflow-init` log, determine whether the failure belongs to generated configuration or the guide, then repair the responsible source and retry. |
| 22 | AutoForge generated Compose repair | Trace the failed `airflow-init` to its generated PostgreSQL connection and add a standalone Airflow database bootstrap before migration. | PASS | The failure was `database "airflow" does not exist` after Level 1's already-initialized PostgreSQL volume. The generator now emits an idempotent `airflow-db-bootstrap` service and makes `airflow-init` wait for it; the exact generator test passed. Next: regenerate Level 2, verify the existing-volume upgrade path, then update the guide only if its instructions need clarification. |
| 23 | `domain_service_workbook.md` Level 2 shared execution loop | Regenerate after the bootstrap repair and start the complete stack against the existing Level 1 PostgreSQL volume. | PASS | The bootstrap service exited successfully after creating/checking the Airflow database. Airflow webserver/scheduler plus RabbitMQ, relay, both workers, application, PostgreSQL, and Redis reached their expected healthy/running states without deleting Level 1 data. |
| 24 | `domain_service_workbook.md` Level 2 missing verification | Determine the real user-owned consumer and internal HTTP path that the guide's old clear condition mentioned but did not show. | PASS | The manifest identifies `application/durable_job_handler.py` as SCAFFOLDED. A deterministic handler test passed, and an authenticated `POST /internal/jobs/daily_profile_check` completed through RabbitMQ with status `succeeded`. The guide now includes these exact steps and lists every new Level 2 `.env` key. Next: validate the edited guide and commit the verified generator/guide/progress changes. |
| 25 | `domain_service_workbook.md` Level 3 | Add Redis cache/distributed-lock YAML, regenerate, then test cache miss/hit and lock competition with generated fakes. | PASS | Generation and port validation passed; the new fake test passed and the existing selected Redis service is healthy. The guide now names the exact fake test instead of only saying to write one. Next: move to the MinIO storage overlay in Level 4. |
| 26 | `domain_service_workbook.md` Level 4 | Add Object Storage YAML, regenerate, and start the documented MinIO overlay. | BLOCKED | Generation again fails at Ruff before the overlay can start. The combined shell command then attempted the overlay from the wrong working directory; that secondary path error made no generated-file change. Next: identify the exact generated Ruff error, repair AutoForge if generator-owned, then retry the guide command from `C:\workspace\profile-server`. |
| 27 | `domain_service_workbook.md` Level 4 retry | Fix the Level 3 guide test formatting, regenerate Object Storage, start MinIO, and test the generated storage fake. | PASS | The blocker was a Ruff formatting error in the new Level 3 example, fixed in both guide and validation output. Regeneration passed; MinIO is healthy and its bucket initializer exited 0; the Object Storage fake round trip passed. The guide now correctly says this Level creates a storage boundary, not an automatic profile-image DB column. Next: commit the Level 3/4 guide corrections and continue to the external-provider Level. |
| 28 | `domain_service_workbook.md` Level 5 | Add External Provider YAML, regenerate, and test the generated fake response boundary. | PASS | Generation succeeded and the fake test passed for 200, 404, and 503 responses. The old guide incorrectly claimed that this response fake also simulated network timeouts; it now states the exact boundary and reserves real timeout/retry validation for an integration test with a configured provider. Next: commit the Level 4/5 guide corrections and continue to Search/Vector/RAG. |
| 29 | `domain_service_workbook.md` Level 6 | Add Search, Vector Store, and RAG YAML then regenerate. | BLOCKED | Generation fails at Ruff before the RAG overlay can start. Next: run Ruff in the generated profile output, correct the exact guide/example formatting defect if present, and retry the same Level 6 generation. |
| 30 | AutoForge Vector Store repair | Trace the remaining Level 6 Ruff error to the generated `PointId` type alias and its import spacing. | PASS | The generator now emits Python 3.12's `type PointId = int | str` with Ruff-compatible import spacing; all five focused Vector Store generator tests passed. Next: publish this generator repair, regenerate Level 6, and start the RAG overlay. |
| 31 | `domain_service_workbook.md` Level 6 | Start the documented `rag` profile after the repaired generation and test the generated Search/Vector fake boundaries. | PASS | The fake test and Ruff check passed. The new idempotent shared-network step created `profile_server-rag`; Qdrant and OpenSearch both reached `healthy`. Ollama was not started and no model was downloaded. Next: follow Level 7 with one delivery boundary at a time. |
| 32 | `domain_service_workbook.md` Level 7 | Add only the Realtime Redis Pub/Sub option, regenerate, and verify its fake hub/backplane delivery contract. | PASS | Generation passed. The fake test and Ruff check passed; the rebuilt generated core stack remained healthy with the same Redis service. The guide now gives this secret-free first Level 7 choice and its exact test; webhook, email, and SMS remain separate later choices because each needs an external provider. Next: follow Level 8's LLM fake boundary. |
| 33 | `domain_service_workbook.md` Level 8 | Add the LLM fake boundary and regenerate. | PASS | After the generator spacing repair, generation and generated-project Ruff passed. The fresh walkthrough exposed one missing setup step: the generated project's optional dependencies were not installed into the Conda environment, so importing its OpenAI boundary failed even for a fake test. Both guides now install the generated server with `.[test]` after generation/re-generation. `test_llm_fake.py`, Ruff, and `import openai` then passed without an API key. Next: follow Level 9 ELK overlay. |
| 34 | `domain_service_workbook.md` Level 9 | Add the central ELK overlay, regenerate, install the generated project, and start the documented Compose command. | PASS | Generation, generated-project dependency installation, and Ruff passed. Elasticsearch, Kibana, and Filebeat all became healthy. A `/health` request produced an `x-request-id`; Filebeat indexed the matching JSON log in Elasticsearch. The guide now gives this exact request-ID verification instead of only saying to inspect Kibana. Next: follow Level 10's single/HA environment boundary. |
| 35 | `domain_service_workbook.md` Level 10 | Enable the generated single-host HA overlay and prepare its required RAG inference dependency. | PASS | Generation, generated-project installation, Ruff, and the combined port preflight passed. The Ollama runtime image (not a model) plus Qdrant/OpenSearch became healthy; three application replicas and Nginx became healthy. The public `/health` returned 200 before and after restarting one application replica. The guide now includes exact single-host commands, the RAG-inference condition, one-replica recovery check, and the harmless ELK orphan warning. Next: the three-document fresh-PC walkthrough is complete; Level 11 is a conceptual extension, not a required login-server setup step. |
| 36 | `README.md` project entry | Re-read the first document as a junior developer and compare its claims with the completed walkthrough. | PASS WITH FIX | The old README presented an obsolete 224-test baseline and an obsolete “next DatabaseSpec” task as current facts. It now gives only the three-document reading order, explains GENERATED/SCAFFOLDED in beginner language, and links implementation status to its proper owner. Next: inspect the Level 11 boundary and validate the documented local links. |
| 37 | Three-document local-link check | Test every local Markdown link before declaring the walkthrough complete. | RETRY | The first checker treated README's repository-root directory as an empty PowerShell path, emitted path-binding errors, then incorrectly printed success. No guide claim was evaluated by that result. Correct the checker to use `.` for root-level documents and retry the same validation. |
| 38 | `domain_service_workbook.md` Level 11 | Inspect whether this Level is an executable part of the junior walkthrough. | PASS WITH FIX | Level 11 has no command because it explains a later AutoForge-maintainer concern, but that boundary was implicit. It now explicitly says it is reference-only and must not be started merely to finish the login/Quest walkthrough. Next: rerun the corrected local-link check and validate the edited Markdown diff. |
| 39 | `README.md` workflow diagram | Compare the visible top-level workflow with the current implementation owner before final validation. | PASS WITH FIX | The diagram still implied automatic commit, push, and Pull Request creation. Current Status says safe Git automation is unimplemented, so the diagram now ends at generation, validation, user-owned domain code, and Docker execution. Next: rerun Markdown-link and diff checks. |
| 40 | Three-document final validation | Recheck every local Markdown link, duplicate heading, and whitespace error after all document edits. | PASS | All local Markdown links resolve, no duplicate headings exist, and `git diff --check` passed. The fresh-PC walkthrough is complete: Levels 1-10 were executed on a reset project environment, while Level 11 is correctly marked as a non-executing reference step. |

### 2026-08-22 재실행: README.md

- [x] 검증 완료
- **발견된 문제점**: 없음. README에는 실행 명령이 없고, 다음 행동이 두 번째 문서로 명확히 연결된다.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: `GENERATED`와 `SCAFFOLDED`의 한 줄 설명 및 세 문서 순서가 초보자에게 충분하다.

### 2026-08-22 재실행: login_server_from_zero.md 0~2절

- [x] 검증 완료
- **발견된 문제점**: Miniconda 설치 직후 일반 PowerShell에서 `conda`가 인식되지 않으면 기존 안내의 `conda init powershell`도 실행할 수 없었다.
- **수정 보완 내역**: `conda`가 없을 때 시작 메뉴의 Miniconda Prompt에서 `conda init powershell`을 실행하고 새 PowerShell에서 재확인하는 정확한 복구 순서를 추가했다.
- **가독성 개선사항**: "conda가 없음"과 "conda activate만 실패"를 서로 다른 상황으로 분리했다. Git 2.51.0, Conda 25.9.1, Docker Desktop client/server 29.1.2, `hello-world` 컨테이너가 모두 실제 실행됐다. 다음: Docker 안전 정리 절을 확인한다.

### 2026-08-22 재실행: login_server_from_zero.md 3절

- [x] 검증 완료
- **발견된 문제점**: 문서 명령 `docker ps -a`와 `docker volume ls`를 실제 실행하니 이전 로그인·프로필 실습 컨테이너와 데이터 볼륨이 남아 있었다. 이 상태는 새 PC 페르소나와 맞지 않는다.
- **수정 보완 내역**: 가이드 자체는 전역 prune을 금지하고 서버별 `docker compose down --volumes`를 제공하므로 수정하지 않는다. login-server와 profile-server의 실제 Compose 구성을 먼저 읽기 전용으로 확인했고, 그 두 프로젝트의 컨테이너·네트워크·볼륨만 문서 명령으로 제거했다.
- **가독성 개선사항**: 전체 Docker 삭제가 아니라 현재 실습의 알려진 Compose 프로젝트만 제거해야 한다는 문서 경계를 실제 목록으로 확인했다. JSON labels로 남은 profile-server RAG·MinIO overlay와 임시 RAG HA 검증 Compose 파일을 특정했다. label이 없는 `realtime_sentinel_ha_...`는 `autoforge-realtime-sentinel-drill-3`의 읽기 전용 bind mount만 쓰는 임시 검증 컨테이너였다. 명시적 profile teardown과 exact 이름 삭제를 끝냈고, 마지막 `docker ps -a`와 `docker volume ls -q`는 모두 빈 결과였다.

### 2026-08-22 재실행: login_server_from_zero.md 4절

- [x] 검증 완료
- **발견된 문제점**: 실제 재실행 환경에 이전 clone, 생성 서버, profile 실습 폴더와 `autoforge` Conda 환경이 남아 있어 문서의 `git clone`과 `conda create`가 그대로는 실패한다.
- **수정 보완 내역**: 이들은 문서가 안내한 새 PC의 외부 경로이므로, 현재 작업 저장소 `C:\AutoForge`를 보존한 채 정확한 다섯 경로와 `autoforge` 환경만 제거했다. 첫 긴 설치 실행 뒤 package import가 보이지 않아 같은 `python -m pip install -e ".[test,server]"` 명령을 단독 재실행했다. 이때 `C:\Users\ldgo9\miniconda3\envs\autoforge\python.exe`가 선택됐고 editable wheel 설치가 성공했다.
- **가독성 개선사항**: 이 정리는 가이드의 첫 실행에는 필요 없으며, 실제 검증 환경을 새 PC 조건으로 되돌리기 위한 준비다. 가이드의 명령 자체에는 누락이 없고, 긴 설치 출력으로 첫 실행의 끝부분이 관찰되지 않았던 검증 환경 이슈였다. 다음: 문서의 CLI와 focused specification test를 실행한다.

### 2026-08-22 재실행: login_server_from_zero.md 5절

- [x] 검증 완료
- **발견된 문제점**: VS Code를 선택 설치라고 했지만 기존 5절은 `code` 명령을 바로 실행하므로 VS Code가 없는 주니어가 명세 파일을 만들 수 없었다.
- **수정 보완 내역**: 세 YAML 파일을 먼저 생성하는 PowerShell 명령을 추가하고, VS Code가 없을 때 Windows Notepad에서 같은 파일을 열어 저장하는 정확한 대체 경로를 추가했다.
- **가독성 개선사항**: 파일 이름을 새로 입력하거나 확장자를 바꾸지 않아도 된다는 점과 YAML의 공백 들여쓰기 규칙을 명시했다. 문서의 New-Item 명령으로 세 파일을 실제 만들고, 각 문서 YAML 본문을 해당 파일에 적용했다. 다음: 생성 명령을 실행한다.

### 2026-08-22 재실행: login_server_from_zero.md 6절

- [x] 검증 완료
- **발견된 문제점**: 없음. 명세 파일 세 개만으로 `Generated and validated 3 units`가 실제 출력됐다.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: 이 단계가 생성기 설치가 아니라 생성된 서버의 선택 의존성을 테스트 환경에 설치하는 단계라는 설명을 확인했다. 생성 명령은 3 units를 검증했고 생성 서버의 `.[test]` installation도 성공했다.

### 2026-08-22 재실행: login_server_from_zero.md 7~8절

- [x] 검증 완료
- **발견된 문제점**: handler와 generated router, `.env.example`은 실제 경로에 있었지만, 검증 중 내가 `migrations\versions\0001_baseline.py`라는 단일 경로를 가정해 조회해 실패했다. 가이드는 이미 `migrations/*/versions/0001_*.py`라고 와일드카드로 설명하므로 문서 결함은 아니다.
- **수정 보완 내역**: 없음. 다음 조회는 문서가 가리킨 실제 와일드카드 범위로 제한한다.
- **가독성 개선사항**: generated router와 사람이 작성할 handler의 물리적 분리가 실제 생성 결과에서 확인됐다. 문서의 migration glob에서 `migrations\identity\versions\0001_identity.py`가 확인됐고, `.env` 복사와 `Validated 2 host-port override(s)` 사전 검사도 성공했다.

### 2026-08-22 재실행: login_server_from_zero.md 9절

- [x] 검증 완료
- **발견된 문제점**: 없음. 생성된 handler의 `NotImplementedError`와 아직 없는 test file은 9절에서 교체·추가하라고 명시한 정상 scaffold 상태였다.
- **수정 보완 내역**: 문서의 `ping() -> PingResponse(message="pong")` 구현과 `tests/test_system_ping.py` 비동기 단위 테스트를 그대로 적용했다.
- **가독성 개선사항**: Router/schema를 다시 작성하지 않고 SCAFFOLDED handler와 행동 테스트만 작성하는 소유권 경계가 실제 파일에서 확인됐다. 문서의 focused pytest가 `1 passed`로 성공했다.

### 2026-08-22 재실행: login_server_from_zero.md 10절

- [x] 검증 완료
- **발견된 문제점**: 없음. 문서의 Compose build·up·wait 명령을 실행했고 image build와 PostgreSQL·Redis·migration·application 생성까지 실제 출력됐다. 긴 build 출력 때문에 최종 `ps` 부분이 도구 출력에서 잘렸으므로, 성공으로 가정하지 않는다. 별도 `ps`에서 application/PostgreSQL/Redis가 모두 healthy였고 `/health`는 `status = ok`를 반환했다. 같은 명령 블록의 ping 호출은 오류 없이 끝났지만 PowerShell 표 출력이 보이지 않아 응답 값을 한 번 더 명확히 표시한다.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: 문서가 제시한 `docker compose ... ps`를 별도 확인 단계로 실행해 health 상태를 명확히 판정한다. application/PostgreSQL/Redis는 모두 healthy였고 `/health`는 `{"status":"ok"}`, `/api/system/ping`은 `{"message":"pong"}`을 실제 반환했다.

### 2026-08-22 재실행: login_server_from_zero.md 11절

- [x] 검증 완료
- **발견된 문제점**: 없음. password helper와 test file은 11절에서 새로 만들도록 한 정상 상태였다.
- **수정 보완 내역**: PBKDF2-SHA256, salt, constant-time compare를 사용하는 문서 본문과 원본/오답 비밀번호 테스트를 그대로 추가했다.
- **가독성 개선사항**: 이 helper는 SCAFFOLDED 파일이며 다음 handler가 CPU hash 작업을 `asyncio.to_thread`로 넘긴다는 연결 설명이 충분하다. 문서의 focused pytest가 `1 passed`로 성공했다.

### 2026-08-22 재실행: login_server_from_zero.md 12~13절

- [x] 검증 완료
- **발견된 문제점**: 없음. identity handler는 문서가 구현하라고 표시한 세 `NotImplementedError`만 가진 정상 scaffold였다.
- **수정 보완 내역**: 회원가입 DB 저장, password hash 검증, Redis SessionData 생성·조회 코드를 문서 본문 그대로 적용했다. 문서의 focused tests는 `2 passed`였고 Docker rebuild·wait 뒤 application/PostgreSQL/Redis가 모두 healthy였다. 첫 signup은 `chimp@example.com`의 UUID와 `is_active: true`를 반환했고, 같은 요청은 409로 차단됐다. Login이 bearer token을 반환했고, 그 token으로 Redis session validate가 같은 user UUID를 반환했다.
- **가독성 개선사항**: PostgreSQL 계정 원장과 Redis 세션의 서로 다른 책임이 실제 handler dependency로 분리된 것을 확인했다. 같은 PowerShell session에서 생성한 token은 application restart 뒤에도 같은 user UUID로 검증됐다.

### 2026-08-22 재실행: login_server_from_zero.md 14~19절

- [x] 검증 완료
- **발견된 문제점**: 없음. `.env`와 `.gitignore`의 `logs/`, `*.env` 제외 규칙은 실제 생성 서버에 있었다.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: 실제 application container는 `C:\workspace\login-server\logs`를 `/app/logs`로 read/write mount했고 네 개의 log file이 있었다. 14절의 테스트 순서는 이번 재실행의 generate → password → ping → health → HTTP → restart 순서와 일치했다. 16절의 HA 키(`postgres_mode`, `application_replicas`, `REDIS_CLUSTER_URL`)도 명세 모델에 존재한다. HA는 문서대로 단일 모드와 별도 output에서 수행하므로 여기서는 실행하지 않는다.

### 2026-08-22 재실행: domain_service_workbook.md Level 0~1

- [x] 검증 완료
- **발견된 문제점**: 없음. Login Guide 1~13절 재실행이 끝났고, `AutoForge v0.1.0`과 Docker client/server가 실제 동작했다. profile spec/output path도 새 PC 조건처럼 존재하지 않았다.
- **수정 보완 내역**: 문서의 Copy-Item 명령으로 세 login-server specification input files를 profile-server-spec에 실제 복사한 뒤, 문서 Level 1의 49200 port·profile package·profile DB 설정으로 project YAML을 교체하고 profile.yaml을 추가했다. 첫 patch 형식은 같은 파일을 delete/add하려 해 도구에서 거절됐고 파일 변경은 없었다; in-place update로 재적용했다. Generate는 `4 units`를 검증했고, profile-server `.[test]` install과 여덟 생성 artifact 확인도 성공했다. raw SQL과 Alembic baseline 모두 `user_profiles`를 만든다. profile `.env` 복사와 port validation도 `Validated 2 host-port override(s)`로 성공했다. 첫 Guide 9~13절의 system/identity SCAFFOLDED handler, password helper, 두 focused test를 `profile_server` prefix로 반복했고 `2 passed`를 확인했다. 마지막으로 4.5의 profile handler 구현을 적용했다.
- **가독성 개선사항**: Level 0의 별도 path·별도 port 원칙은 실제로 실행 중인 login-server를 유지하면서 다음 Level을 시작할 수 있게 한다. Profile 명세는 current_session과 idempotency를 Router dependency로 선언하므로 handler가 Redis header 처리를 직접 하지 않는다. 다음: 문서 4.6의 Profile Compose build·migration·health를 실행한다.

### 2026-08-22 재실행: domain_service_workbook.md Level 1 4.5절 기동 확인

- [x] 검증 완료
- **발견된 문제점**: 없음. 이전 실행 셀의 완료 상태는 세션 정리로 보존되지 않아, 성공으로 가정하지 않고 별도 상태 명령으로 재확인했다.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: `application`, `postgres`, `redis`가 모두 `healthy`이고, `http://127.0.0.1:49200/health`가 `{"status":"ok"}`를 반환했다. 다음은 문서 4.6절의 Profile API와 멱등성 검증이다.

### 2026-08-22 재실행: domain_service_workbook.md Level 1 4.6절 첫 저장·재전송

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: 실제 가입은 활성 사용자 UUID를 반환했고, 같은 Bearer token과 같은 `Idempotency-Key`로 보낸 두 PUT 응답은 같은 `updated_at`을 반환하여 마지막 비교가 `True`였다. 다음은 Bearer 조회와 같은 key의 다른 본문에 대한 409 검증이다.

### 2026-08-22 재실행: domain_service_workbook.md Level 1 4.6절 Bearer 조회·충돌 차단

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: Bearer token 조회는 저장된 `Chimp` 프로필을 반환했고, 같은 `Idempotency-Key`에 다른 `display_name`을 보낸 요청은 실제로 409로 차단됐다. 다음은 문서가 안내한 세 Compose 로그 확인이다.

### 2026-08-22 재실행: domain_service_workbook.md Level 1 4.6절 진단 로그

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: `logs application`, `logs postgres`, `logs redis` 세 명령이 모두 실제 실행됐다. application 로그에는 signup/login/profile PUT 200, 같은 key의 다른 body PUT 409가 남았고, PostgreSQL은 ready, Redis는 accept connections 상태를 보였다. Level 0~1 검증을 실제 실행으로 완료했다.

### 2026-08-22 재실행: domain_service_workbook.md Level 2 명세 병합

- [x] 명세 조각 적용
- **발견된 문제점**: 없음. 기존 `application.services` 아래에 `session`만 있었고, `durable_jobs`는 없었다.
- **수정 보완 내역**: 문서의 `events` RabbitMQ/Outbox 조각과 `daily_profile_check` Durable Job 조각을 기존 `application` 항목에 한 번만 병합했다.
- **가독성 개선사항**: 같은 최상위 항목을 중복 생성하지 않고 `services`와 `durable_jobs`의 역할을 분리했다. 다음은 문서 공통 네 단계의 generate다.

### 2026-08-22 재실행: domain_service_workbook.md Level 2 generate

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: 명세 조각 병합 뒤에도 generator가 실제로 `Generated and validated 4 units`를 반환했다. 다음은 생성된 서버의 test 의존성 설치다.

### 2026-08-22 재실행: domain_service_workbook.md Level 2 generated package install

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: 재생성된 서버에 `aio-pika`를 포함한 의존성이 설치됐고 editable wheel 설치도 성공했다. 다음은 기존 `.env`에 새 Level 2 환경값을 명시적으로 반영하는 단계다.

### 2026-08-22 재실행: domain_service_workbook.md Level 2 환경 병합

- [x] 검증 완료
- **발견된 문제점**: 없음. 기존 `.env`에는 Level 2가 요구하는 9개 환경값이 없었다.
- **수정 보완 내역**: `.env.example`에서 새로 생긴 RabbitMQ, Airflow, Durable Job 관련 9줄만 기존 `.env`에 추가했고 기존 값은 덮어쓰지 않았다.
- **가독성 개선사항**: 먼저 예시 파일과 현재 파일의 key를 비교해 필요한 줄만 복사했다. 다음은 port preflight다.

### 2026-08-22 재실행: domain_service_workbook.md Level 2 port preflight

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: `validate-ports`가 새 환경 파일에서 `5 host-port override(s)`를 유효하다고 확인했다. 다음은 전체 Compose 기동과 healthy 상태 확인이다.

### 2026-08-22 재실행: domain_service_workbook.md Level 2 Compose build

- [x] 검증 완료
- **발견된 문제점**: Compose build·기동 명령은 image 생성과 RabbitMQ/Airflow/worker 컨테이너 생성까지 실제로 진행했다. 별도 상태 표에서 RabbitMQ·application·PostgreSQL·Redis는 healthy였고, outbox-relay·message-worker·durable-job-worker·Airflow webserver는 막 시작한 healthcheck 초기화 상태였다.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: 재확인 결과 RabbitMQ, application, outbox-relay, message-worker, durable-job-worker, Airflow webserver, PostgreSQL, Redis가 모두 healthy였다. migrate·airflow-init·airflow-db-bootstrap은 예상대로 exit code 0으로 완료됐다.

### 2026-08-22 재실행: domain_service_workbook.md Level 2 healthcheck 재확인

- [x] 검증 완료
- **발견된 문제점**: 대기 뒤 상태를 출력한 도구 세션은 최종 `ps` 결과를 보존하지 않았지만, 단독 상태 확인으로 해결됐다.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: 단독 `docker compose ps --all`에서 최종 상태를 확인하는 방식으로 긴 Compose 출력의 한계를 우회했다. 다음은 2.1절 사용자 소유 handler다.

### 2026-08-22 재실행: domain_service_workbook.md Level 2.1 Durable Job handler

- [x] SCAFFOLDED 구현 적용
- **발견된 문제점**: 없음. 생성된 handler는 문서가 예상한 `NotImplementedError` scaffold였다.
- **수정 보완 내역**: 문서의 결정론적 `job_type`·`run_key` 반환 구현으로 교체했다.
- **가독성 개선사항**: RabbitMQ 연결·Outbox relay·상태 전이는 생성 인프라에 남기고, 사용자 소유 handler는 결과 계산만 담당한다. 다음은 문서의 focused test 추가다.

### 2026-08-22 재실행: domain_service_workbook.md Level 2.1 Durable Job test 작성

- [x] 테스트 추가
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 문서의 `DurableJobExecution` fixture와 결과 assertion을 새 focused test 파일로 추가했다.
- **가독성 개선사항**: Docker·RabbitMQ를 시작하기 전에 사용자 handler만 빠르게 검증할 수 있다. 다음은 해당 focused pytest 실행이다.

### 2026-08-22 재실행: domain_service_workbook.md Level 2.1 Durable Job focused test

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: 문서의 focused test가 실제로 `1 passed`였다. 다음은 2.2절의 내부 HTTP 요청으로 전체 비동기 경로를 검증한다.

### 2026-08-22 재실행: domain_service_workbook.md Level 2.2 내부 Job 요청

- [x] 검증 완료
- **발견된 문제점**: 긴 빌드 출력 때문에 첫 HTTP 결과가 보이지 않았지만, application과 worker healthy 상태를 독립 확인한 뒤 요청만 재실행해 결과를 확보했다.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: 실제 내부 API 응답은 `status: succeeded`였고 `result.run_key`가 요청한 run key와 같았다. Level 2의 DB 기록·Outbox·RabbitMQ·Worker 경로를 실제 실행으로 완료했다.

### 2026-08-22 재실행: domain_service_workbook.md Level 3 명세 병합

- [x] 명세 조각 적용
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 문서의 Redis key-value store와 distributed lock 조각을 기존 `tooling` 항목에 병합했다.
- **가독성 개선사항**: 세션, cache, lock은 같은 Redis 인스턴스를 써도 서로 다른 namespace와 protocol 계약을 사용한다. 다음은 공통 generate 단계다.

### 2026-08-22 재실행: domain_service_workbook.md Level 3 generate

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: generator가 다시 `Generated and validated 4 units`를 반환했다. 다음은 재생성된 서버 의존성 설치다.

### 2026-08-22 재실행: domain_service_workbook.md Level 3 generated package install

- [x] 검증 완료
- **발견된 문제점**: 패키지 설치 직전 `PROGRESS.md`를 외부 작업 폴더 기준 상대 경로로 읽으려 해 읽기 명령이 실패했다. 이는 가이드 결함이 아니라 검증자가 상태 파일에 절대 경로를 쓰지 않은 절차 오류다.
- **수정 보완 내역**: 이후 모든 상태 파일 읽기는 `C:\AutoForge\PROGRESS.md` 절대 경로만 사용한다. 이어진 `python -m pip install -e ".[test]"`는 실제로 성공했다.
- **가독성 개선사항**: 작업 폴더가 바뀌는 walkthrough에서는 상태 파일의 절대 경로가 필수다. 다음은 port preflight다.

### 2026-08-22 재실행: domain_service_workbook.md Level 3 port preflight

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: `validate-ports`가 현재 환경에서 `5 host-port override(s)`를 유효하다고 확인했다. 다음은 재생성된 Compose 환경 기동이다.

### 2026-08-22 재실행: domain_service_workbook.md Level 3 Compose rebuild

- [x] 검증 완료
- **발견된 문제점**: 긴 Compose 출력만 잘렸고 별도 상태 명령은 정상 동작했다.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: `ps redis`는 Redis가 실제로 healthy임을 보였다. 다음은 생성된 fake를 이용한 cache·lock focused test다.

### 2026-08-22 재실행: domain_service_workbook.md Level 3 fake test 작성

- [x] 테스트 추가
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 문서의 cache miss/hit 및 lock 경쟁 assertion을 focused test 파일로 추가했다.
- **가독성 개선사항**: runtime Redis 전에도 cache key와 lock token 해제 규칙을 빠르게 검증할 수 있다. 다음은 focused pytest 실행이다.

### 2026-08-22 재실행: domain_service_workbook.md Level 3 fake test 실행

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: cache miss/hit, lock 경쟁, 잘못된 token의 해제 차단, 올바른 token의 해제가 실제로 `1 passed`였다. Level 3을 완료하고 다음은 Object Storage 경계다.

### 2026-08-22 재실행: domain_service_workbook.md Level 4 명세 병합

- [x] 명세 조각 적용
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 문서의 `storage` 조각을 기존 `tooling` 항목에 병합했다.
- **가독성 개선사항**: 이 단계는 Profile table에 binary column을 추가하지 않고 S3 호환 storage 계약과 선택 가능한 MinIO overlay만 생성한다. 다음은 공통 generate 단계다.

### 2026-08-22 재실행: domain_service_workbook.md Level 4 generate

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: generator가 Object Storage 조각을 포함해 `Generated and validated 4 units`를 반환했다. 다음은 공통 의존성 설치와 port preflight다.

### 2026-08-22 재실행: domain_service_workbook.md Level 4 package·preflight

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: S3 호환 client 의존성이 실제로 설치됐고 `validate-ports`가 `5 host-port override(s)`를 통과했다. 다음은 기본 Compose와 MinIO overlay 검증이다.

### 2026-08-22 재실행: domain_service_workbook.md Level 4 기본 Compose rebuild

- [x] 검증 완료
- **발견된 문제점**: 기본 Compose 재빌드는 실제 image build를 수행했고, 별도 상태 표에서 PostgreSQL·Redis·RabbitMQ·Airflow webserver는 healthy였다. application과 worker 네 개는 막 재생성되어 `health: starting`이었다.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: 정상 초기화 뒤 application, outbox-relay, message-worker, durable-job-worker도 모두 healthy였다. 다음은 별도 MinIO overlay다.

### 2026-08-22 재실행: domain_service_workbook.md Level 4 MinIO 환경 파일

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: `deploy/storage/.env.example`을 같은 디렉터리의 로컬 `.env`로 문서대로 복사했다.
- **가독성 개선사항**: storage runtime 설정은 기본 application `.env`와 분리된다. 다음은 MinIO Compose profile 기동이다.

### 2026-08-22 재실행: domain_service_workbook.md Level 4 MinIO Compose

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: MinIO는 기본 Profile Compose와 별도 프로젝트·port로 기동됐고 `minio-init`은 exit code 0으로 완료됐다. Level 4를 실제 실행으로 완료했다.

### 2026-08-22 재실행: domain_service_workbook.md Level 4 Object Storage fake test 작성

- [x] 테스트 추가
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 문서의 put/get/list/delete round-trip focused test를 추가했다.
- **가독성 개선사항**: 실제 credential 없이도 handler가 사용할 Object Storage contract를 검증할 수 있다. 다음은 focused pytest 실행이다.

### 2026-08-22 재실행: domain_service_workbook.md Level 4 Object Storage fake test 실행

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: Object Storage fake round-trip이 실제로 `1 passed`였다. 다음은 MinIO와 버킷 초기화 컨테이너의 최종 상태 확인이다.

### 2026-08-22 재실행: domain_service_workbook.md Level 5 명세 병합

- [x] 명세 조각 적용
- **발견된 문제점**: 없음.
- **수정 보완 내역**: External Provider 경계 조각을 기존 `tooling`에 병합했다.
- **가독성 개선사항**: 실제 provider URL·API key는 추가하지 않았다. 다음은 공통 generate 단계다.

### 2026-08-22 재실행: domain_service_workbook.md Level 5 generate

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: generator가 `Generated and validated 4 units`를 반환했다. 다음은 common package·preflight·Compose 단계다.

### 2026-08-22 재실행: domain_service_workbook.md Level 5 package·preflight

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: External Provider transport 의존성을 포함한 editable install과 `5 host-port override(s)` preflight가 실제로 통과했다. 다음은 기본 Compose rebuild다.

### 2026-08-22 재실행: domain_service_workbook.md Level 5 Compose rebuild

- [x] 검증 완료
- **발견된 문제점**: 실제 기본 Compose 재빌드는 image build를 수행했고, 별도 상태 표에서 application은 막 재생성되어 `health: starting`이었다.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: 정상 초기화 뒤 application은 healthy였다. 다음은 External Provider fake의 선언된 응답 순서 검증이다.

### 2026-08-22 재실행: domain_service_workbook.md Level 5 External Provider fake test 작성

- [x] 테스트 추가
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 문서의 200·404·503 선언 응답 focused test를 추가했다.
- **가독성 개선사항**: 실제 URL이나 API key 없이 provider 경계의 정상·클라이언트 오류·서버 오류 계약을 검증한다. 다음은 focused pytest다.

### 2026-08-22 재실행: domain_service_workbook.md Level 5 External Provider fake test 실행

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: 문서의 200·404·503 응답 순서 테스트가 실제로 `1 passed`였다. Level 5를 완료하고 다음은 Search·Vector Store·RAG 경계다.

### 2026-08-22 재실행: domain_service_workbook.md Level 6 명세 병합

- [x] 명세 조각 적용
- **발견된 문제점**: 없음.
- **수정 보완 내역**: Search, Vector Store, RAG 조각을 기존 `tooling`에 병합했다.
- **가독성 개선사항**: keyword 검색, vector 검색, RAG overlay는 각각 독립된 선택 항목이다. Ollama 모델 다운로드나 실제 답변 생성은 이 단계에 포함되지 않는다. 다음은 common generate다.

### 2026-08-22 재실행: domain_service_workbook.md Level 6 generate

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: generator가 Search·Vector Store·RAG 계약을 포함해 `Generated and validated 4 units`를 반환했다. 다음은 package install과 환경값 비교다.

### 2026-08-22 재실행: domain_service_workbook.md Level 6 package install

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: 재생성된 서버의 editable install이 실제로 성공했다. 다음은 `.env.example`과 기존 `.env`의 새 key 비교다.

### 2026-08-22 재실행: domain_service_workbook.md Level 6 환경 비교

- [x] 검증 완료
- **발견된 문제점**: 재생성된 기본 `.env.example`에 `RAG_*` 5개 key가 새로 나타났지만, Level 6의 별도 절은 이 값들을 `deploy/rag/.env`에서 사용하도록 안내한다. 공통 환경 병합 문장만 읽으면 초보자가 기본 `environment/.env`에 잘못 복사할 수 있다.
- **수정 보완 내역**: 공통 절에 `deploy/storage`와 `deploy/rag` overlay의 값은 기본 `environment/.env`가 아니라 해당 디렉터리의 `.env`로 복사한다는 문장을 추가했다. 기본 `.env`에는 RAG key를 추가하지 않았다.
- **가독성 개선사항**: storage·RAG처럼 별도 Compose overlay를 쓰는 Level은 해당 `deploy/.../.env`가 정본임을 명시했다.

### 2026-08-22 재실행: domain_service_workbook.md Level 6 port preflight

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: 기본 환경의 `validate-ports`가 실제로 `5 host-port override(s)`를 통과했다. 다음은 기본 Compose rebuild와 RAG overlay 기동이다.

### 2026-08-22 재실행: domain_service_workbook.md Level 6 기본 Compose rebuild

- [x] 검증 완료
- **발견된 문제점**: 실제 기본 Compose 재빌드는 image build를 수행했고, 별도 상태 표에서 application은 막 재생성되어 `health: starting`이었다.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: 정상 초기화 뒤 application은 healthy였다. 다음은 별도 RAG overlay 환경 파일과 network 준비다.

### 2026-08-22 재실행: domain_service_workbook.md Level 6 RAG 환경·network

- [x] 검증 완료
- **발견된 문제점**: 없음. `RAG_NETWORK_NAME`은 `profile_server-rag`로 읽혔고 network inspect/create 분기가 오류 없이 끝났다.
- **수정 보완 내역**: `deploy/rag/.env.example`을 별도 `deploy/rag/.env`로 복사했다.
- **가독성 개선사항**: 기본 Compose와 optional overlay는 private network를 공유하되 환경 파일은 분리된다. 다음은 `rag` profile 기동이다.

### 2026-08-22 재실행: domain_service_workbook.md Level 6 RAG Compose

- [x] 검증 완료
- **발견된 문제점**: Qdrant와 OpenSearch는 별도 RAG Compose project에서 생성됐고, 시작 직후 모두 `health: starting` 상태였다. 대기 명령의 마지막 상태 출력은 도구 세션에서 보존되지 않았다.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: Qdrant와 OpenSearch는 모두 healthy였다. Ollama 컨테이너·모델 다운로드는 실행하지 않았다. 다음은 Search·Vector fake test다.

### 2026-08-22 재실행: domain_service_workbook.md Level 6 Search·Vector fake test 작성

- [x] 테스트 추가
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 문서의 SearchService·VectorStore default boundary assertion을 focused test로 추가했다.
- **가독성 개선사항**: index/collection 기본값과 fake client 경계만 검증하며, embedding·hybrid ranking·권한 필터는 도메인 책임으로 남는다. 다음은 focused pytest다.

### 2026-08-22 재실행: domain_service_workbook.md Level 6 Search·Vector fake test 실행

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: Search document와 Vector point의 default index/collection 경계 test가 실제로 `1 passed`였다. Level 6을 완료하고 다음은 realtime·notification 계약이다.

### 2026-08-22 재실행: domain_service_workbook.md Level 7 명세 병합

- [x] 명세 조각 적용
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 문서의 최소 시작점대로 `realtime`과 Redis Pub/Sub backplane만 추가했다. Webhook·SMTP·SOLAPI의 주소와 비밀값은 추가하지 않았다.
- **가독성 개선사항**: 실제 수신처 없이 live hint 계약을 먼저 검증한다. 다음은 common generate다.

### 2026-08-22 재실행: domain_service_workbook.md Level 7 generate

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: generator가 Realtime contract를 포함해 `Generated and validated 4 units`를 반환했다. 다음은 common package·preflight·Compose 단계다.

### 2026-08-22 재실행: domain_service_workbook.md Level 7 package·preflight

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: editable install과 `5 host-port override(s)` preflight가 실제로 통과했다. 다음은 기본 Compose rebuild다.

### 2026-08-22 재실행: domain_service_workbook.md Level 7 Compose rebuild

- [x] 검증 완료
- **발견된 문제점**: 실제 Compose 재빌드는 image build를 수행했지만 긴 Docker 출력 때문에 마지막 상태 표가 보이지 않았다.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: application은 정상 초기화 뒤 healthy였다. 다음은 Realtime hub/backplane fake delivery test다.

### 2026-08-22 재실행: domain_service_workbook.md Level 7 Realtime fake test 작성

- [x] 테스트 추가
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 문서의 hub subscribe·backplane publish·subscriber 수신 assertion을 focused test로 추가했다.
- **가독성 개선사항**: 실제 WebSocket client나 외부 수신 주소 없이 live hint 전달 계약을 검증한다. 다음은 focused pytest다.

### 2026-08-22 재실행: domain_service_workbook.md Level 7 Realtime fake test 실행

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: Realtime hub/backplane의 channel 전달 contract가 실제로 `1 passed`였다. Level 7을 완료하고 다음은 LLM 경계다.

### 2026-08-22 재실행: domain_service_workbook.md Level 8 명세 병합

- [x] 명세 조각 적용
- **발견된 문제점**: 없음. 문서 예시의 model placeholder는 실제 API key 없이도 fake 경계를 생성하는지 확인하기 위한 값이다.
- **수정 보완 내역**: `llm` 조각을 문서 그대로 기존 `tooling`에 병합했고 `OPENAI_API_KEY`는 추가하지 않았다.
- **가독성 개선사항**: fake 검증과 실제 외부 모델 연결을 분리한다. 다음은 common generate다.

### 2026-08-22 재실행: domain_service_workbook.md Level 8 generate

- [x] 검증 완료
- **발견된 문제점**: 없음. 문서의 model placeholder로도 generator가 성공했다.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: LLM transport/fake 계약이 실제로 생성됐다. 다음은 package install과 환경 key 비교다.

### 2026-08-22 재실행: domain_service_workbook.md Level 8 package install

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: OpenAI SDK를 포함한 editable install이 실제로 성공했으며 실제 API key는 사용하지 않았다.
- **가독성 개선사항**: SDK 설치와 외부 API 호출은 별개다. 다음은 `.env.example`의 새 key와 fake-only 단계의 관계를 확인한다.

### 2026-08-22 재실행: domain_service_workbook.md Level 8 환경 비교

- [x] 검증 완료
- **발견된 문제점**: 없음. 새 기본 환경 예시에는 이전 RAG overlay key만 남아 있고 `OPENAI_API_KEY`는 추가되지 않았다.
- **수정 보완 내역**: 없음. fake-only 단계이므로 기본 `.env`에 API key를 추가하지 않는다.
- **가독성 개선사항**: 실제 key 주입은 외부 모델을 연결하는 별도 단계에서만 한다. 다음은 port preflight다.

### 2026-08-22 재실행: domain_service_workbook.md Level 8 port preflight

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: 기본 환경의 `validate-ports`가 실제로 `5 host-port override(s)`를 통과했다. 다음은 기본 Compose rebuild다.

### 2026-08-22 재실행: domain_service_workbook.md Level 8 Compose rebuild

- [x] 검증 완료
- **발견된 문제점**: 실제 Compose 재빌드는 image build를 수행했지만 긴 Docker 출력 때문에 마지막 상태 표가 보이지 않았다.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: application은 healthy였다. 다음은 API key 없이 수행하는 LLM fake test다.

### 2026-08-22 재실행: domain_service_workbook.md Level 8 LLM fake test 작성

- [x] 테스트 추가
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 문서의 LLM message·instructions·fake response assertion을 focused test로 추가했다.
- **가독성 개선사항**: 실제 OpenAI API key나 network 호출 없이 request/response 경계를 검증한다. 다음은 focused pytest다.

### 2026-08-22 재실행: domain_service_workbook.md Level 8 LLM fake test 실행

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: API key 없이 LLM request/response contract test가 실제로 `1 passed`였다. Level 8을 완료하고 다음은 로그 observability overlay다.

### 2026-08-22 재실행: domain_service_workbook.md Level 9 명세 병합

- [x] 명세 조각 적용
- **발견된 문제점**: 없음.
- **수정 보완 내역**: central ELK 조각을 기존 `tooling`에 병합했다.
- **가독성 개선사항**: application은 file log만 남기고, 별도 overlay의 Filebeat가 수집한다. 다음은 common generate다.

### 2026-08-22 재실행: domain_service_workbook.md Level 9 generate

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: generator가 ELK overlay를 포함해 `Generated and validated 4 units`를 반환했다. 다음은 common package·preflight다.

### 2026-08-22 재실행: domain_service_workbook.md Level 9 package·preflight

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: editable install과 `5 host-port override(s)` preflight가 실제로 통과했다. 다음은 ELK overlay Compose 기동이다.

### 2026-08-22 재실행: domain_service_workbook.md Level 9 ELK Compose

- [x] 검증 완료
- **발견된 문제점**: Elasticsearch와 Filebeat는 healthy였고 Kibana는 시작 직후 `health: starting` 상태였다.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: Elasticsearch·Filebeat·Kibana가 모두 healthy였다. 다음은 Filebeat가 application file log에서 request ID를 실제 수집하는지 확인한다.

### 2026-08-22 재실행: domain_service_workbook.md Level 9 Filebeat request ID 검색

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: health 요청의 실제 `x-request-id`가 Filebeat index에서 검색됐고, 결과에는 `path: /health`, `status_code: 200`, 같은 request ID와 application log file path가 포함됐다. Level 9를 완료하고 다음은 single-host HA다.

### 2026-08-22 재실행: domain_service_workbook.md Level 10 명세 병합

- [x] 명세 조각 적용
- **발견된 문제점**: 현재 명세에는 database provider/mode와 single-host 항목이 명시돼 있지 않았다.
- **수정 보완 내역**: 문서의 예시대로 PostgreSQL standalone·MySQL standalone 선택값을 `local_environment`에 명시하고, `single_host.enabled: true`, `application_replicas: 3`을 추가했다.
- **가독성 개선사항**: Kubernetes, Control Plane heartbeat, service token은 문서가 실제 image·Secret·namespace가 준비될 때만 선택하라고 하므로 추가하지 않는다. 다음은 common generate다.

### 2026-08-22 재실행: domain_service_workbook.md Level 10 generate

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: generator가 single-host HA contract를 포함해 `Generated and validated 4 units`를 반환했다. 다음은 generated package install과 runtime.env 준비다.

### 2026-08-22 재실행: domain_service_workbook.md Level 10 package·runtime environment

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: generated package editable install이 성공했고, 없던 `deploy/single-host/runtime.env`를 문서대로 example에서 생성했다.
- **가독성 개선사항**: HA overlay의 runtime 값은 기본 environment와 분리된다. 다음은 두 환경 파일을 함께 쓰는 port preflight다.

### 2026-08-22 재실행: domain_service_workbook.md Level 10 HA port preflight

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: 기본 environment와 single-host runtime environment를 함께 넣은 `validate-ports`가 `5 host-port override(s)`를 통과했다. 다음은 RAG inference runtime 준비다.

### 2026-08-22 재실행: domain_service_workbook.md Level 10 RAG inference runtime

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: Qdrant·OpenSearch·Ollama runtime이 모두 healthy였다. Ollama model 데이터는 내려받지 않았다. 다음은 Nginx와 3 application replica를 포함한 single-host overlay다.

### 2026-08-22 재실행: domain_service_workbook.md Level 10 single-host HA Compose 상태

- [x] 검증 완료
- **발견된 문제점**: 없음. 앞선 build 출력이 잘려 최종 상태를 가정하지 않고 별도 `docker compose ps --all`로 확인했다.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: application 3개와 nginx는 모두 healthy였고, PostgreSQL·Redis·RabbitMQ·Airflow·ELK도 함께 정상 상태였다. 다음은 공개 Nginx endpoint와 한 replica 재시작 중 무중단 응답 확인이다.

### 2026-08-22 재실행: domain_service_workbook.md Level 10 public health·replica restart

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: Nginx 공개 endpoint의 재시작 전 HTTP status는 200이었고, application replica 하나를 실제 재시작한 뒤 30초 이내 public health가 `ok`로 복구됐다. 한 대 PC에서 container-level HA 복구 범위를 실제 확인했다. 다음은 workbook 종료 절의 공통 확인 목록과 최종 guide 검증이다.

### 2026-08-22 재실행: domain_service_workbook.md 공통 전체 pytest 첫 시도

- [ ] 환경 전환 필요
- **발견된 문제점**: 자동화 셸의 기본 Python(`C:\Users\ldgo9\miniconda3\python.exe`)에는 pytest가 설치돼 있지 않아 `No module named pytest`로 끝났다.
- **수정 보완 내역**: 없음. 첫 가이드가 `conda activate autoforge`를 이미 지시하므로 문서 누락이 아니라 현재 셸이 그 활성화 단계를 거치지 않은 환경 차이다.
- **가독성 개선사항**: 다음 실행은 가이드의 `autoforge` Conda 환경을 명시적으로 활성화해 같은 테스트를 다시 수행한다.

### 2026-08-22 재실행: domain_service_workbook.md 공통 전체 pytest(Conda 활성 환경)

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: 첫 가이드가 만든 `autoforge` Conda 환경에서 생성 Profile Server의 전체 테스트가 실제로 `10 passed`였다. 다음은 세 진입 문서의 링크·서식과 AutoForge 변경 diff의 최종 확인이다.

### 2026-08-22 재실행: 세 진입 문서 최종 Markdown·diff 검증

- [x] 검증 완료
- **발견된 문제점**: 없음.
- **수정 보완 내역**: 없음.
- **가독성 개선사항**: README와 두 가이드의 로컬 Markdown 링크는 모두 해석됐고 `git diff --check`도 통과했다. 이번 재실행에서 문서 결함으로 확인된 것은 Conda 복구 경로, VS Code 없는 파일 생성 경로, overlay 환경 파일 복사 위치 세 가지이며 모두 해당 Guide에 최소 수정으로 반영됐다.
