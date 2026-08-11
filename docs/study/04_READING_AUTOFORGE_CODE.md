# 4권: AutoForge 실제 코드 읽기

> **문서 역할: STUDY / CODE READING GUIDE**
> 이 문서는 코드를 읽는 순서를 안내한다. Architecture 정본은
> [`system_design.md`](../architecture/system_design.md)와 연결된 Canonical
> Architecture가 소유한다.

## 1. 코드를 읽는 방법

파일을 처음부터 끝까지 외우지 않는다. 다음 질문을 하나씩 답한다.

1. 이 파일은 어떤 계층에 있는가?
2. 외부에서 무엇을 입력받는가?
3. 무엇을 반환하는가?
4. 파일이나 외부 Process를 직접 다루는가?
5. 어떤 테스트가 동작을 보장하는가?

## 2. 첫 번째: Registry

읽을 파일:

```text
src/autoforge/core/registry/registry.py
tests/core/test_registry.py
```

확인할 것:

- 객체를 어떤 ID로 등록하는가?
- 같은 ID를 두 번 등록하면 어떻게 되는가?
- 없는 ID를 조회하면 어떻게 되는가?
- `names()`가 왜 정렬된 결과를 반환하는가?

실행:

```powershell
pytest tests/core/test_registry.py -v
```

Registry는 작기 때문에 테스트와 구현의 연결을 연습하기 좋다.

## 3. 두 번째: Specification

읽을 파일:

```text
src/autoforge/core/specification/models.py
src/autoforge/core/specification/naming.py
tests/core/test_specification_models.py
```

`ProjectSpec`부터 찾는다.

```python
class ProjectSpec(StrictSpecModel):
    spec_version: Literal["1"]
    project: ProjectInfo
    application: ApplicationSpec
    tooling: ToolingSpec
```

해석:

- `ProjectSpec`은 `StrictSpecModel`을 상속한다.
- `spec_version`에는 현재 문자열 `"1"`만 허용된다.
- `project`에는 `ProjectInfo` 객체가 필요하다.
- `application`에는 `ApplicationSpec` 객체가 필요하다.
- `tooling`에는 생성 도구와 실행 환경 선택을 담은 `ToolingSpec`이 들어간다.

`field_validator`는 필드 하나를 검사하고 `model_validator`는 여러 필드의
관계를 검사한다.

실행:

```powershell
pytest tests/core/test_specification_models.py -v
```

## 4. 세 번째: Project Generator

읽을 파일:

```text
src/autoforge/services/generation/fastapi_project.py
tests/services/test_fastapi_project_generator.py
```

먼저 `render()`만 읽는다. `_render_*` 보조 함수는 나중에 본다.

```python
def render(
    self,
    specification: ProjectSpec,
) -> dict[PurePosixPath, str]:
```

입력은 `ProjectSpec`, 출력은 경로와 파일 내용의 Dictionary다.

다음으로 `plan()`을 읽는다.

```python
rendered_files = self.render(specification)
```

같은 렌더링 결과를 기준으로 각 파일의 Hash와 소유권을 `PlannedFile`에
기록한다.

실행:

```powershell
pytest tests/services/test_fastapi_project_generator.py -v
```

## 5. 네 번째: Resolver

읽을 파일:

```text
src/autoforge/services/generation/plan_resolver.py
tests/services/test_generation_plan_resolver.py
```

테스트 이름을 먼저 읽는다. 테스트 이름이 각 정책을 설명한다.

```text
파일이 없으면 CREATE인가?
같은 파일이면 KEEP인가?
사용자가 변경했으면 CONFLICT인가?
이전 Manifest가 안전하면 REPLACE_GENERATED인가?
```

실행:

```powershell
pytest tests/services/test_generation_plan_resolver.py -v
```

## 6. 다섯 번째: Applier

읽을 파일:

```text
src/autoforge/services/generation/plan_applier.py
tests/services/test_generation_plan_applier.py
```

Resolver와의 차이를 계속 확인한다.

```text
Resolver = 행동 결정, 파일 쓰지 않음
Applier  = 전체 재검사 후 파일 씀
```

특히 충돌이 하나라도 있을 때 다른 파일도 쓰지 않는 테스트를 찾는다.

## 7. 여섯 번째: Validator

읽을 파일:

```text
src/autoforge/services/validation/project_validator.py
src/autoforge/infrastructure/process/runner.py
tests/services/test_project_validator.py
```

`ProjectValidator`는 명령 순서를 결정하고 `AsyncioProcessRunner`는 실제 외부
프로세스를 실행한다.

```text
Service        = 무엇을 어떤 순서로 검증할지
Infrastructure = 운영체제에서 명령을 어떻게 실행할지
```

실행:

```powershell
pytest tests/services/test_project_validator.py -v
```

Stub Runner를 쓰는 테스트와 실제 Process를 쓰는 테스트의 차이를 확인한다.

## 8. 일곱 번째: Plugin Adapter

읽을 파일:

```text
src/autoforge/core/plugin/generator.py
src/autoforge/core/plugin/validator.py
tests/core/test_generator_plugin.py
tests/core/test_validator_plugin.py
```

Adapter가 기존 Generator를 상속해 다시 구현하는지, 내부 객체에 호출을
위임하는지 확인한다. AutoForge는 composition을 사용한다.

```text
상속: "나는 기존 Generator의 한 종류다."
조합: "나는 기존 Generator를 내부에 가지고 사용한다."
```

## 9. 여덟 번째: Built-in Catalog

읽을 파일:

```text
src/autoforge/plugins/catalog.py
tests/plugins/test_catalog.py
```

Catalog는 새로운 생성 규칙을 구현하지 않는다. 이미 존재하는 Registry를
한곳에서 조립한다.

확인할 것:

- package name을 인자로 받는가?
- ProcessRunner를 인자로 받는가?
- 호출마다 새 Registry를 만드는가?
- 전역 Catalog가 존재하지 않는가?

## 10. 수직 통합 테스트

마지막으로 읽을 파일:

```text
tests/services/test_fastapi_generation_flow.py
```

이 테스트는 Project와 Module을 생성하고 실제 FastAPI Endpoint를 호출한다.
작은 단위 테스트를 이해한 뒤 읽어야 흐름이 보인다.

```powershell
pytest tests/services/test_fastapi_generation_flow.py -v
```

## 11. 디버깅할 때 순서

테스트가 실패하면 다음 순서로 본다.

1. 실패한 테스트 이름
2. 마지막 Assertion
3. 실제 값과 예상 값
4. 테스트가 호출한 공개 메서드
5. 그 메서드 내부의 분기
6. 관련 모델의 Validator

처음부터 전체 Repository를 다시 읽지 않는다.

## 12. 직접 해 볼 안전한 연습

코드를 바꾸기 전 테스트만 실행해 본다.

```powershell
pytest tests/core/test_registry.py -v
pytest tests/services/test_fastapi_project_generator.py -v
pytest tests/plugins/test_catalog.py -v
```

그다음 테스트의 객체 이름과 구현 파일의 클래스 이름을 서로 찾아본다.

예:

```text
test_builtin_catalog_contains_expected_plugins
                ↓
create_builtin_plugin_catalog
                ↓
create_fastapi_generator_plugins
create_project_validator_plugins
```

## 이번 권에서 기억할 것

```text
테스트 이름부터 읽는다.
입력과 반환값을 먼저 찾는다.
한 파일의 계층 책임을 확인한다.
단위 테스트 후 수직 통합 테스트를 읽는다.
코드를 외우지 말고 데이터 흐름을 따라간다.
```

더 자세한 사전식 설명은
[AutoForge 상세 학습 가이드](../AUTOFORGE_STUDY_GUIDE_2026-07-30.md)를
참고한다.
