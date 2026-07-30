# AutoForge 코드·아키텍처 학습 가이드

- 작성일: 2026-07-30
- 대상: Python과 FastAPI를 다시 공부하며 AutoForge를 이해하려는 개발자
- 현재 기준: AutoForge v0.1.0, pytest 224개 통과

> 이 문서가 어렵다면 먼저
> [AutoForge 완전 입문 학습 시리즈](study/README.md)를 1권부터 읽는다.
> 이 문서는 시리즈를 읽은 뒤 개념을 찾아보는 상세 참고서다.

## 0. 개발 용어를 빼고 먼저 이해하기

### 우리가 최종적으로 하고 싶은 일

새로운 FastAPI 서버를 만들 때마다 사람은 비슷한 파일을 반복해서 작성한다.

```text
main.py
설정 파일
회원 Router
주문 Router
요청/응답 클래스
서비스 클래스
테스트
Dockerfile
CI/CD 설정
```

서버가 하나라면 직접 작성해도 된다. 하지만 게임 서버, 자동매매 서버,
관리자 서버처럼 프로젝트가 늘어나면 같은 구조를 계속 복사하게 된다.

AutoForge가 최종적으로 하려는 일은 다음과 같다.

```text
사람:
"프로젝트 이름은 KIS Auto Trading이고,
 account와 trading 기능이 필요해."

AutoForge:
"그러면 필요한 폴더와 기본 파일을 만들고,
 테스트와 빌드까지 확인할게.
 이미 사람이 작성한 코드는 건드리지 않을게."
```

즉 AutoForge는 웹서버를 대신 실행하는 프로그램이 아니라, 웹서버 프로젝트를
만들어 주는 프로그램이다.

### common-tool과 무엇이 다른가

기존 `common-tool`도 코드를 만들어 줬다.

```text
common-tool:
설정 읽기 → 파일 생성 → 사람이 생성된 파일 수정
```

AutoForge는 생성 전후에 안전 절차를 추가한다.

```text
AutoForge:
주문서 검사
→ 만들 파일을 미리 계산
→ 기존 사용자 파일과 충돌하는지 확인
→ 안전할 때만 파일 생성
→ 무엇을 만들었는지 기록
→ 생성된 서버가 실제로 실행 가능한지 검사
```

가장 중요한 차이는 단순히 파일을 찍어내는 것이 아니라, 반복 실행해도 사용자
코드를 잃지 않도록 만드는 것이다.

## 0.1 식당 비유로 전체 구조 이해하기

AutoForge를 식당이라고 생각해 보자.

```text
Specification  = 손님이 작성한 주문서
Generator      = 주문서를 보고 요리 방법을 정하는 요리사
GenerationPlan = 요리하기 전에 작성한 작업 목록
Resolver       = 재료와 주방 상태를 확인하는 담당자
Applier        = 실제로 요리하는 담당자
Manifest       = 무엇을 사용하고 만들었는지 적은 영수증
Validator      = 음식이 제대로 만들어졌는지 검사하는 품질 담당자
Workspace      = 이 주문에만 사용하는 조리대
Plugin         = 새로운 종류의 요리를 만드는 추가 조리 도구
Registry       = 어떤 조리 도구가 어디 있는지 기록한 목록
Pipeline       = 주문부터 배달까지의 작업 순서
EventBus       = "요리 완료" 같은 소식을 필요한 사람에게 전달
```

이 비유를 실제 AutoForge 작업에 대입하면 다음과 같다.

```text
1. 주문서
   "kis_auto_trading이라는 FastAPI 서버를 만들어 주세요."

2. 요리사
   "pyproject.toml, main.py, health.py와 테스트가 필요하겠군."

3. 작업 목록
   "총 12개 파일을 만들 예정입니다."

4. 주방 상태 확인
   "main.py는 없으니 생성 가능.
    handlers.py는 사람이 이미 수정했으니 보존."

5. 실제 작업
   안전하다고 판정된 파일만 디스크에 기록.

6. 영수증
   "10개 생성, 2개 보존"과 각 파일의 Hash를 기록.

7. 품질 검사
   Import, pytest, Ruff, wheel build를 실행.
```

한 번에 기억하기 어렵다면 다음 세 줄만 먼저 기억한다.

```text
Specification은 주문서다.
Plan은 아직 실행하지 않은 작업 목록이다.
Manifest는 실제 작업이 끝난 뒤의 영수증이다.
```

## 0.2 AutoForge를 사용하지 않고 직접 만든다면

FastAPI 프로젝트를 손으로 만들 때는 대략 다음 작업을 한다.

```text
1. 폴더 생성
2. pyproject.toml 작성
3. src/kis_auto_trading/main.py 작성
4. FastAPI 객체 생성
5. Router 작성
6. Request/Response 모델 작성
7. 테스트 작성
8. pytest 실행
9. lint 실행
10. package build 확인
```

AutoForge는 1~10번에서 반복 가능한 부분을 자동화하려는 것이다. 하지만
매매 전략이나 계좌 위험 관리처럼 프로젝트마다 다른 핵심 로직까지 마음대로
자동 생성하려는 것은 아니다.

```text
AutoForge가 소유:
반복 가능한 폴더 구조, Schema 연결, Router 연결, 설정과 테스트 골격

사람이 소유:
매매 전략, 주문 판단, 위험 관리, 프로젝트만의 비즈니스 규칙
```

## 0.3 가장 작은 실제 예제

아직 완성된 `generate` CLI는 없으므로 현재 내부 코드의 사용 모습을 단순화해
보면 다음과 같다.

```python
from autoforge.core.specification import (
    ApplicationSpec,
    ProjectInfo,
    ProjectSpec,
)
from autoforge.services.generation import FastAPIProjectGenerator


# 1. 무엇을 만들지 주문서를 작성한다.
specification = ProjectSpec(
    spec_version="1",
    project=ProjectInfo(
        name="KIS Auto Trading",
        package_name="kis_auto_trading",
        version="0.1.0",
        description="자동매매 서버",
    ),
    application=ApplicationSpec(
        modules=[],
    ),
)

# 2. FastAPI 프로젝트를 만들 수 있는 Generator를 준비한다.
generator = FastAPIProjectGenerator()

# 3. 생성될 파일 내용을 메모리에서 계산한다.
rendered_files = generator.render(specification)

# 4. 파일을 쓰기 전에 작업 계획을 만든다.
plan = generator.plan(specification)
```

한 줄씩 살펴보자.

```python
specification = ProjectSpec(...)
```

`ProjectSpec`은 단순한 Dictionary가 아니다. 잘못된 프로젝트 이름, 버전과
알 수 없는 항목을 검사하는 Pydantic 모델이다.

```python
generator = FastAPIProjectGenerator()
```

FastAPI 프로젝트 구조를 만드는 규칙을 가진 객체를 생성한다. 여기서는 아직
파일이 만들어지지 않는다.

```python
rendered_files = generator.render(specification)
```

생성될 경로와 파일 내용을 메모리에서 계산한다. 아직 디스크에 쓰지 않는다.

```python
plan = generator.plan(specification)
```

각 파일을 생성할지, 보존할지, 충돌로 처리할지 판단하기 위한 초기 계획을
만든다. 실제 기존 파일과 비교하는 작업은 Resolver가 맡는다.

현재 구현에서는 이 뒤에 Resolver, Applier와 Validator를 각각 조립해야 한다.
향후 CLI와 Pipeline이 완성되면 사용자는 내부 객체를 하나씩 호출하지 않고
명령 한 번으로 이 전체 순서를 실행하게 된다.

## 0.4 왜 이렇게 여러 단계로 나눴는가

처음 보면 “그냥 파일을 쓰면 되는데 왜 이렇게 복잡하지?”라고 느낄 수 있다.

다음 상황을 생각해 보자.

```text
첫째 날:
AutoForge가 handlers.py를 생성함.

둘째 날:
사람이 handlers.py에 실제 주문 코드를 300줄 작성함.

셋째 날:
명세에 Endpoint 하나를 추가하고 AutoForge를 다시 실행함.
```

Generator가 무조건 파일을 덮어쓰면 300줄이 사라진다. 그래서 AutoForge는
파일마다 소유자를 정하고, 이전 내용의 Hash를 Manifest에 남기며, 다음 실행
때 파일이 변경됐는지 확인한다.

여러 단계는 멋있어 보이기 위한 구조가 아니라 사용자 코드를 잃지 않기 위한
안전장치다.

## 0.5 지금 당장 전부 이해할 필요가 없는 것

처음 공부할 때 다음 항목은 이름만 알고 넘어가도 된다.

- 외부 Plugin의 의존성 정렬 알고리즘
- Entrypoint의 동적 Python Import
- GenerationJobManifest의 복수 Unit 검증
- 향후 Git Webhook과 CI/CD 구조
- 아직 구현하지 않은 Database Plugin

먼저 다음 네 가지만 이해한다.

```text
1. ProjectSpec에 만들 서버 정보를 담는다.
2. Generator가 파일 내용과 Plan을 만든다.
3. Applier가 안전한 파일만 쓴다.
4. Validator가 생성 결과를 테스트한다.
```

## 1. 한 문장으로 이해하기

AutoForge는 사람이 반복해서 작성하던 FastAPI 프로젝트 구조를 검증 가능한
명세로 생성하고, 기존 사용자 코드를 보호하며, 테스트와 빌드에 성공한
결과만 향후 Git 자동화로 전달하기 위한 Python 코드 생성 플랫폼이다.

AutoForge 자체가 웹서버인 것은 아니다. AutoForge가 만드는 결과물이
`game_server`, `kis-auto-trading` 같은 독립 FastAPI 웹서버다.

```text
AutoForge                         생성 결과
코드 생성 및 검증 도구       →    독립 FastAPI 프로젝트
```

현재 구현은 로컬 생성과 검증 기반까지다. GitHub Webhook, 자동 Commit/Push,
Pull Request와 AI 생성은 아직 구현하지 않았다.

## 2. 왜 만드는가

C# `common-tool`은 설정과 명령으로 Application, Template, Packet, Protocol,
Controller와 DB 관련 반복 코드를 만들었다. 생성된 `game-server`를 사람이
조금씩 수정하는 방식이었다.

AutoForge는 그 장점을 계승하면서 다음 문제를 해결하려 한다.

- 생성 코드와 사람 코드가 섞이는 문제
- 재생성 때 덮어써도 되는 파일을 판단하기 어려운 문제
- 생성 결과의 테스트와 빌드가 보장되지 않는 문제
- 생성, Git, 배포 책임이 한곳에 섞이는 문제
- 기능 확장 지점과 실행 순서가 불명확한 문제

```text
설정 기반 코드 생성
  + Specification 입력 검증
  + Plan과 Manifest 변경 추적
  + Workspace 파일 경계
  + Plugin 기능 확장
  + Validator의 Import/Test/Lint/Build
  + 향후 Pipeline과 Git 자동화
```

첫 실제 적용 대상은 `kis-auto-trading`이다. SKN12의 기능을 파일 단위로
복사하는 것이 아니라, 반복 구조는 AutoForge가 생성하고 매매 전략 같은
고유 로직은 사람이 소유하도록 분리한다.

## 3. 전체 실행 흐름

```text
사용자 입력(YAML/CLI, 향후 Git Event)
                 │
                 ▼
          Specification
       생성할 대상의 검증된 설계도
                 │
                 ▼
             Generator
       파일 내용과 초기 계획 작성
                 │
                 ▼
          GenerationPlan
      쓰기 전에 무엇을 할지 표현
                 │
                 ▼
      GenerationPlanResolver
      현재 파일과 비교해 행동 결정
                 │
                 ▼
       GenerationPlanApplier
      안전성 재검사 후 파일 적용
                 │
                 ▼
       GenerationManifest
       실제 결과와 출처 기록
                 │
                 ▼
       ProjectValidator
      Import → pytest → Ruff → wheel
```

Plugin은 이 흐름을 대체하지 않는다. Generator와 Validator 같은 기능을
교체하거나 추가할 수 있게 감싸는 확장 구조다.

## 4. 저장소 구조와 추천 탐색 순서

```text
src/autoforge/
├── cli/                 명령행 입력과 출력
├── core/                프레임워크 독립 계약과 안전 정책
│   ├── generation/      Plan, Manifest, Generator 계약
│   ├── job/             여러 생성 단위를 묶는 Job 결과
│   ├── plugin/          Metadata, Loader, Adapter
│   ├── registry/        이름으로 객체를 보관
│   ├── specification/   Project와 Module 명세
│   └── workspace/       안전한 파일 경계
├── infrastructure/      외부 Process와 파일시스템 Adapter
├── plugins/             AutoForge 기본 Plugin 조립
└── services/
    ├── generation/      FastAPI 생성과 Plan 적용
    └── validation/      생성 프로젝트 검증
```

처음 읽을 때 추천 순서:

1. `core/specification/models.py`
2. `services/generation/fastapi_project.py`
3. `core/generation/models.py`
4. `services/generation/plan_resolver.py`
5. `services/generation/plan_applier.py`
6. `services/validation/project_validator.py`
7. `core/plugin/generator.py`
8. `core/plugin/validator.py`
9. `plugins/catalog.py`
10. 같은 이름을 가진 `tests/`의 테스트

처음부터 PluginLoader의 모든 예외 처리나 미래 Pipeline을 이해하려 하지
말고, 한 프로젝트가 생성되고 검증되는 수직 흐름부터 이해하는 것이 좋다.

## 5. Specification: 무엇을 만들 것인가

Specification은 생성 대상의 검증된 데이터다.

```python
from autoforge.core.specification import (
    ApplicationSpec,
    ProjectInfo,
    ProjectSpec,
)

specification = ProjectSpec(
    spec_version="1",
    project=ProjectInfo(
        name="KIS Auto Trading",
        package_name="kis_auto_trading",
        version="0.1.0",
        description="자동매매 FastAPI 서버",
    ),
    application=ApplicationSpec(
        framework="fastapi",
        modules=["account", "trading"],
    ),
)
```

- `spec_version`: Generator와 명세의 호환성 기준
- `package_name`: Python import 이름
- `modules`: Application에 연결할 모듈 목록

Pydantic은 잘못된 입력을 Generator 실행 전에 막는다.

```python
ProjectInfo(
    name="잘못된 예",
    package_name="kis-auto-trading",  # Python import 이름으로 부적합
    version="0.1.0",
)
```

공통 모델 설정:

```python
model_config = ConfigDict(
    extra="forbid",
    str_strip_whitespace=True,
)
```

- `extra="forbid"`: 정의하지 않은 필드를 거부
- `str_strip_whitespace=True`: 문자열 앞뒤 공백 제거

CLI, YAML, Web UI, Git Event와 향후 AI가 모두 같은 Specification을 만들면
입력 방식과 Generator를 분리할 수 있다.

## 6. Generator: 어떻게 만들 것인가

Generator는 Specification을 받아 두 결과를 만든다.

```python
generator.render(specification)  # 경로별 파일 내용
generator.plan(specification)    # 쓰기 전 변경 계획
```

현재 Project Generator는 `FastAPIProjectGenerator`다. `render()` 결과의
개념적 형태는 다음과 같다.

```python
{
    PurePosixPath("pyproject.toml"): "...",
    PurePosixPath("src/kis_auto_trading/main.py"): "...",
    PurePosixPath("src/kis_auto_trading/routers/health.py"): "...",
    PurePosixPath("tests/test_health.py"): "...",
}
```

Generator가 바로 파일을 쓰지 않는 이유는 전체 결과를 먼저 검사하고
Dry-run을 제공하기 위해서다. `PurePosixPath`는 디스크에 접근하지 않는
논리적 상대경로이므로 Windows에서도 Manifest 경로를 결정적으로 유지한다.

## 7. Plan, Resolver, Applier, Manifest

### GenerationPlan

Plan은 실행 결과가 아니라 “이렇게 처리하고 싶다”는 예정표다.

```text
CREATE             새 파일 생성
REPLACE_GENERATED  이전 생성 파일의 안전한 교체
KEEP               현재 파일 유지
SKIP               생성하지 않음
CONFLICT           안전하게 판단할 수 없어 중단
```

각 파일에는 경로, Generator ID/버전, 소유권, 행동, Specification Hash,
예상 Content Hash와 출처가 기록된다.

### GenerationPlanResolver

Generator의 초기 계획과 현재 Workspace 및 이전 Manifest를 비교한다.

```text
파일 없음                     → CREATE
동일한 GENERATED 파일         → KEEP
안전한 이전 생성 파일         → REPLACE_GENERATED
사용자가 수정한 GENERATED     → CONFLICT
이미 존재하는 SCAFFOLDED      → KEEP
USER_OWNED                    → 생성하거나 교체하지 않음
```

Resolver는 판단만 하고 파일을 쓰지 않는다.

### GenerationPlanApplier

실제 쓰기 직전에 다음을 다시 검사한다.

- Plan과 렌더링 경로가 일치하는가?
- 명세와 Content Hash가 일치하는가?
- 충돌 파일이 있는가?
- Plan 이후 대상 파일이 바뀌지 않았는가?
- 모든 경로가 Workspace 내부인가?

판단과 실행 사이에 파일이 변경될 수 있으므로 재검사가 필요하다.

### GenerationManifest

Manifest는 실제 작업 결과다.

```text
CREATED / CHANGED / UNCHANGED / PRESERVED
SKIPPED / CONFLICT / FAILED
```

```text
Specification = 설계도
Plan          = 작업 예정표
Manifest      = 작업 영수증
```

Manifest의 Generator 버전, 출처와 Hash는 다음 재생성의 안전 근거가 된다.

## 8. 파일 소유권

### GENERATED

명세로 완전히 재현 가능한 파일이다.

```text
application/generated/module_registry.py
modules/trading/generated/schemas.py
modules/trading/generated/router.py
```

이전 Manifest와 현재 내용이 모두 일치할 때만 교체한다.

### SCAFFOLDED

최초 한 번 골격을 만들고 이후 사람이 관리한다.

```text
README.md
modules/trading/handlers.py
modules/trading/service.py
```

재생성해도 기존 사용자 구현을 보존한다.

### USER_OWNED

처음부터 사용자가 소유한다. AutoForge는 생성하거나 교체하지 않는다.

Python에는 C# `partial class`와 같은 기능이 없으므로 생성 코드와 사용자
코드를 파일 단위로 분리한다.

## 9. Workspace와 Validator

Workspace는 AutoForge가 파일을 다룰 수 있는 작업 경계다.

```python
workspace.resolve(PurePosixPath("src/app/main.py"))
```

`../outside.py`, 절대경로, Windows Drive 경로와 경로 이탈은 거부한다.
이는 OS Sandbox 전체가 아니라 애플리케이션 수준의 파일 안전 경계다.

`ProjectValidator`는 생성 프로젝트를 순서대로 검증한다.

```text
1. package.main Import
2. pytest
3. Ruff lint
4. wheel Package Build
```

```python
result = await process_runner.run(
    ("python", "-m", "pytest"),
    cwd=workspace.root,
    timeout_seconds=30.0,
)
```

- Shell 문자열 대신 인자 튜플 사용
- 실행 위치를 Workspace로 고정
- Timeout 적용
- 종료 코드, stdout, stderr와 실행 시간 반환
- 실패하면 이후 단계 중단

## 10. Plugin 관련 용어

### Registry

이름으로 객체를 보관하고 찾는다. 중복 등록을 거부한다. 객체를 자동으로
검색하거나 실행하지 않는다.

### Plugin Metadata

Plugin의 ID, 버전, API 버전, Capability, 지원 명세 버전, 의존성, Permission,
Entrypoint를 선언한다.

- Capability: 제공하는 기능
- Permission: 필요한 외부 접근

Permission은 현재 선언과 검증만 하며 OS 수준 Sandbox를 제공하지 않는다.

### Adapter

기존 Generator나 Validator를 변경하지 않고 Plugin Metadata와 연결한다.

```text
FastAPIProjectGenerator + PluginMetadata
                    ↓
          GeneratorPluginAdapter
```

### BuiltinPluginCatalog

AutoForge 기본 Generator와 Validator Registry를 조립한다.

```python
catalog = create_builtin_plugin_catalog(
    package_name="kis_auto_trading",
    process_runner=AsyncioProcessRunner(),
)
```

호출마다 새로운 Registry를 만들어 여러 작업과 테스트가 전역 상태를
공유하지 않는다.

### PluginLoader

외부 Plugin 디렉터리를 다룬다.

- `discover()`: Python 코드를 실행하지 않고 Manifest 발견
- `resolve_load_order()`: 의존성 버전과 순환 검사
- `load_trusted()`: 명시적으로 신뢰한 Entrypoint만 실행

```text
Registry = 이름표가 붙은 보관함
Adapter  = 기존 구현과 Plugin 계약의 연결부
Catalog  = AutoForge 내장 Plugin 조립 결과
Loader   = 외부 Plugin 발견과 trusted 로딩
Manager  = 범용 Plugin 등록과 실행 관리
```

## 11. EventBus, Task, Pipeline

```text
Pipeline = 무엇을 어떤 순서로 실행할지 결정
EventBus = 실행 중 무슨 일이 일어났는지 Handler에 전달
Task     = 하나의 실행 단위
```

예정된 Pipeline:

```text
ValidateSpec → ResolvePlugins → PrepareWorkspace
→ PlanGeneration → Generate → Validate → Build → Delivery
```

현재 EventBus와 Task 기반은 있지만 전체 생성 흐름에 연결된 Pipeline 실행기는
없다. `ProjectValidator`가 임시로 검증 단계의 순서를 직접 관리한다.

## 12. 생성되는 FastAPI 서버

```text
generated-project/
├── pyproject.toml
├── README.md
├── src/<package_name>/
│   ├── main.py
│   ├── application/
│   │   ├── app_factory.py
│   │   └── generated/module_registry.py
│   ├── modules/
│   └── routers/health.py
└── tests/test_health.py
```

### main.py와 Application Factory

```python
from kis_auto_trading.application.app_factory import create_app

app = create_app()
```

```python
from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="KIS Auto Trading", version="0.1.0")
    app.include_router(health_router)
    return app
```

전역에서 모든 Service를 즉시 초기화하지 않고 함수에서 Application을
조립한다. 테스트 격리와 의존성 주입이 쉬워진다.

실행 명령:

```powershell
uvicorn kis_auto_trading.main:app --reload
```

- `kis_auto_trading.main`: import할 모듈
- `app`: 모듈 안의 FastAPI 객체
- `--reload`: 개발 중 파일 변경 시 재시작

### APIRouter와 Endpoint

```python
from fastapi import APIRouter

router = APIRouter(prefix="/api/trading", tags=["trading"])


@router.get("/orders/{order_id}")
async def get_order(order_id: str) -> OrderResponse:
    return OrderResponse(order_id=order_id, status="pending")
```

- `APIRouter`: 관련 Endpoint 묶음
- `@router.get`: 함수를 HTTP GET 경로에 등록하는 Decorator
- `{order_id}`: URL Path Parameter
- `async def`: 비동기 함수
- `-> OrderResponse`: 반환 타입 힌트

### Pydantic Request와 Response

```python
from pydantic import BaseModel, Field


class CreateOrderRequest(BaseModel):
    symbol: str = Field(min_length=1)
    quantity: int = Field(gt=0)


class OrderResponse(BaseModel):
    order_id: str
    status: str
```

```python
@router.post("/orders", response_model=OrderResponse)
async def create_order(
    request: CreateOrderRequest,
) -> OrderResponse:
    return OrderResponse(order_id="order-1", status="created")
```

FastAPI가 JSON 요청을 Pydantic 모델로 검증하고 OpenAPI 문서를 만든다.

### Depends

```python
from typing import Annotated
from fastapi import Depends


def get_order_service() -> OrderService:
    return OrderService()


@router.post("/orders")
async def create_order(
    request: CreateOrderRequest,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> OrderResponse:
    return await service.create(request)
```

Handler가 전역 객체를 찾지 않고 필요한 객체를 전달받는다. 테스트에서는
Dependency를 가짜 Service로 교체할 수 있다.

### lifespan

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await database.start()
    try:
        yield
    finally:
        await database.stop()
```

- `yield` 이전: 서버 시작
- `yield` 이후: 서버 종료
- `finally`: 오류가 발생해도 정리

Database와 Queue 계약이 정해진 뒤 생성 코드에 확장할 영역이다.

## 13. Python 문법 복습

### 타입 힌트와 Union

```python
def get_name(user_id: int) -> str:
    ...

description: str | None
```

타입 힌트는 IDE와 검사 도구가 오류를 찾게 한다. `str | None`은 문자열 또는
`None`이며 이전의 `Optional[str]`와 같다.

### dataclass

```python
@dataclass(frozen=True, slots=True)
class BuiltinPluginCatalog:
    generators: FastAPIGeneratorPlugins
```

- `@dataclass`: 반복적인 생성자와 비교 코드 생성
- `frozen=True`: 필드 재할당 방지
- `slots=True`: 선언하지 않은 속성 추가 방지

### Protocol

```python
class ProcessRunner(Protocol):
    async def run(...) -> ProcessResult: ...
```

명시적 상속 없이 필요한 메서드 구조를 만족하면 사용할 수 있다. 테스트에서
실제 Process Runner 대신 Stub을 주입하기 쉽다.

### 제네릭과 Enum

```python
GeneratorPluginRegistry[ProjectSpec]
GeneratorPluginRegistry[ModuleSpec]
```

같은 구현을 쓰면서 내부 타입을 구분한다.

```python
class PlannedAction(StrEnum):
    CREATE = "create"
    KEEP = "keep"
```

임의 문자열 대신 허용된 상태만 사용한다.

### async와 await

```python
async def validate() -> Result:
    result = await process_runner.run(...)
    return result
```

`async def`는 Coroutine을 정의하고 실제 결과가 필요할 때 `await`한다.
I/O 대기 시간을 효율적으로 활용하지만 CPU 계산을 자동으로 빠르게 하지는
않는다.

## 14. pytest 테스트 읽기

```python
def test_registry_returns_registered_plugin() -> None:
    registry = Registry[object]()
    plugin = object()

    registry.register("example", plugin)

    assert registry.get("example") is plugin
```

```text
Arrange  준비
Act      실행
Assert   결과 확인
```

예외 테스트:

```python
with pytest.raises(ValueError, match="already registered"):
    registry.register("example", duplicate)
```

비동기 테스트:

```python
@pytest.mark.anyio
async def test_validator() -> None:
    result = await validator.validate(...)
    assert result.succeeded
```

추천 순서:

1. `tests/core/test_registry.py`
2. `tests/core/test_specification_models.py`
3. `tests/services/test_fastapi_project_generator.py`
4. `tests/services/test_generation_plan_resolver.py`
5. `tests/services/test_generation_plan_applier.py`
6. `tests/services/test_project_validator.py`
7. `tests/plugins/test_catalog.py`

테스트는 사용 예제이자 현재 보장되는 동작의 계약이다.

## 15. 현재 구현 상태

### 완료

- Registry와 PluginManager
- Plugin Metadata, 발견, 의존성 정렬과 trusted 로딩
- Generator/Validator Plugin Adapter와 Registry
- Built-in Plugin Catalog
- ProjectSpec, ModuleSpec와 공통 Type System
- FastAPI Project/Module/Schema/Router/Handler 생성
- 사용자 Handler 보존
- Plan, Manifest와 안전한 재생성
- Workspace 경로 보호와 격리 Workspace
- 생성 프로젝트 Import, pytest, Ruff와 wheel 검증
- GenerationJob 결과 모델
- 전체 pytest 224개 통과

### 부분 구현

- CLI: `version`만 완성, `generate`와 `plugin`은 미구현 상태를 명시
- Permission: 선언과 검증만 있고 OS Sandbox 강제는 없음
- Pipeline: 기본 자리만 있고 실행 조정기는 없음
- EventBus와 Task: 기반은 있지만 전체 생성 흐름에 미연결

### 아직 없음

- DatabaseSpec과 Repository Generator
- SQLAlchemy와 Alembic Plugin
- Cache, Queue, WebSocket Blueprint
- 전체 Generation Pipeline
- Git Checkout/Branch/Commit/Push/PR
- GitHub Webhook
- CI/CD와 Kubernetes 자동화
- AI 명세 및 코드 생성 보조

다음 단계는 DB 코드를 바로 만드는 것이 아니라 DatabaseSpec과 Repository
계약의 최소 경계를 정하는 것이다. Table과 Domain Model 관계, DB Type,
비동기 Session, Migration 소유권, 생성 Repository와 사용자 Query의 경계를
먼저 정해야 프로젝트 전용 구조가 범용 Generator에 굳지 않는다.

## 16. 직접 따라 할 학습 순서

```powershell
conda activate autoforge
python -m autoforge.main version
pytest
```

예상 결과는 `AutoForge v0.1.0`, `224 passed`다.

이후 다음 테스트를 순서대로 실행하며 구현과 나란히 읽는다.

```powershell
pytest tests/core/test_specification_models.py -v
pytest tests/services/test_fastapi_project_generator.py -v
pytest tests/services/test_generation_plan_resolver.py -v
pytest tests/services/test_generation_plan_applier.py -v
pytest tests/services/test_fastapi_generation_flow.py -v
pytest tests/plugins/test_catalog.py -v
```

## 17. 반드시 기억할 원칙

1. AutoForge와 생성된 FastAPI 서버는 별도 프로젝트다.
2. Specification은 생성 대상을, Generator는 구현 방법을 안다.
3. Generator는 바로 쓰지 않고 먼저 Plan을 만든다.
4. Resolver는 판단하고 Applier는 검증 후 적용한다.
5. Manifest는 다음 재생성의 안전 근거다.
6. 생성 코드와 사용자 코드는 파일 소유권으로 분리한다.
7. Workspace 밖의 파일은 다루지 않는다.
8. Plugin은 확장 단위이고 Pipeline은 실행 순서를 담당한다.
9. EventBus는 사건을 전달할 뿐 실행 순서를 대신하지 않는다.
10. 검증 성공 전에는 Git에 반영하지 않는다.
11. 프로젝트 전용 비즈니스 로직을 범용 Generator에 넣지 않는다.
12. 구현된 사실과 미래 설계를 구분한다.

## 18. 관련 문서

- `docs/PROJECT_GUIDE_2026-07-29.md`: 전체 목표와 상세 현황
- `docs/architecture/system_design.md`: 시스템 전체 설계
- `docs/architecture/generation_contract.md`: 생성과 소유권 계약
- `docs/architecture/specification_design.md`: 명세 설계
- `docs/architecture/plugin_system.md`: Plugin 구조
- `.codex/current_status.md`: 현재 완료 상태
- `.codex/next_task.md`: 다음 작업 범위
- `.codex/roadmap.md`: 장기 구현 순서

문서와 코드가 다르면 현재 테스트와 실제 소스 코드를 사실 기준으로 삼고,
문서 불일치를 함께 수정한다.
