# 3권: AutoForge 아키텍처 이해하기

## 1. 왜 FastAPI 코드를 자동 생성하는가

2권에서 만든 작은 서버도 파일과 기능이 늘어나면 반복 작업이 생긴다.

```text
새 프로젝트마다:
pyproject.toml 작성
main.py와 Application Factory 작성
Router와 Schema 작성
테스트 작성
모듈 등록
lint와 build 확인
```

복사해서 이름만 바꾸면 빠르지만 누락과 오래된 코드도 함께 복사할 수 있다.
AutoForge는 반복 가능한 부분을 명세 기반으로 생성하고 검증한다.

## 2. 주문서에서 검증까지

```text
ProjectSpec
  → Generator
  → GenerationPlan
  → Resolver
  → Applier
  → Manifest
  → Validator
```

각 단계가 한 가지 질문에 답한다.

| 단계 | 질문 |
|---|---|
| ProjectSpec | 무엇을 만들 것인가? |
| Generator | 어떤 파일 내용이 필요한가? |
| Plan | 어떤 파일 작업을 할 예정인가? |
| Resolver | 현재 상태에서 각 작업은 안전한가? |
| Applier | 검사 결과대로 실제 파일을 적용할 수 있는가? |
| Manifest | 실제로 무슨 일이 일어났는가? |
| Validator | 생성 결과가 import, test, lint, build에 성공하는가? |

## 3. ProjectSpec

```python
specification = ProjectSpec(
    spec_version="1",
    project=ProjectInfo(
        name="KIS Auto Trading",
        package_name="kis_auto_trading",
        version="0.1.0",
    ),
    application=ApplicationSpec(
        modules=["account", "trading"],
    ),
)
```

일반 Dictionary 대신 Pydantic 모델을 쓰므로 잘못된 이름과 버전을 일찍
거부한다. Generator는 검증된 입력만 받는다.

## 4. Generator와 render

```python
generator = FastAPIProjectGenerator()
rendered = generator.render(specification)
```

`rendered`는 아직 디스크에 쓴 파일이 아니다.

```python
{
    PurePosixPath("pyproject.toml"): "파일 내용",
    PurePosixPath("src/kis_auto_trading/main.py"): "파일 내용",
}
```

메모리에서 먼저 만들면 결과를 검사하고 Dry-run으로 보여 줄 수 있다.

## 5. Plan과 Resolver

```python
plan = generator.plan(specification)
resolved_plan = resolver.resolve(plan, workspace)
```

Generator는 원하는 작업을 적고 Resolver는 실제 파일 상태와 비교해 최종
행동을 정한다.

```text
CREATE / REPLACE_GENERATED / KEEP / SKIP / CONFLICT
```

Resolver가 파일을 쓰지 않는 이유는 안전 여부를 모두 판단하기 전에 일부
파일만 변경되는 것을 피하기 위해서다.

## 6. Applier와 Manifest

```python
manifest = applier.apply(
    job_id="job-1",
    plan=resolved_plan,
    rendered_files=rendered,
    workspace=workspace,
)
```

Applier는 쓰기 직전에 경로와 Hash를 다시 확인한다. Manifest에는 실제 생성,
변경, 보존과 실패 결과가 기록된다.

```text
Plan     = 작업 전 예정표
Manifest = 작업 후 영수증
```

## 7. 파일 소유권

사용자 코드 보호를 위해 파일에 소유권을 부여한다.

| 소유권 | 의미 |
|---|---|
| GENERATED | 명세로 완전히 재현 가능 |
| SCAFFOLDED | 최초 골격만 생성하고 이후 사용자 소유 |
| USER_OWNED | AutoForge가 생성하거나 변경하지 않음 |

예를 들어 Router 연결 파일은 GENERATED가 될 수 있지만 실제 주문 로직이 담긴
Handler는 SCAFFOLDED로 만들어 이후 보존한다.

## 8. Hash가 필요한 이유

Hash는 긴 파일 내용을 짧고 일정한 문자열로 계산한 결과다. 내용이 조금만
달라져도 다른 Hash가 나온다.

```text
이전 Manifest Hash == 현재 파일 Hash
→ AutoForge가 마지막으로 기록한 뒤 사용자가 바꾸지 않았다고 판단 가능
```

Hash만으로 파일의 의미를 이해하는 것은 아니다. 변경 여부를 빠르고
결정적으로 비교하는 도구다.

## 9. Workspace

Workspace는 한 생성 작업이 파일을 다룰 수 있는 폴더다.

```text
C:\temp\autoforge\job-123\
```

`../outside.py`처럼 밖으로 나가는 경로를 거부한다. 작업별 Workspace를
분리하면 두 작업이 같은 파일을 동시에 변경할 위험도 줄어든다.

## 10. Validator

생성됐다는 사실만으로 정상 서버라는 뜻은 아니다.

```text
Import
→ pytest
→ Ruff
→ wheel build
```

하나라도 실패하면 검증 실패다. 향후 Git 자동화는 검증 성공 결과만
Commit하도록 설계할 예정이다.

## 11. Plugin은 무엇인가

AutoForge가 FastAPI만 영원히 지원한다면 구현을 직접 연결해도 된다. 하지만
앞으로 DB, Queue, Git Provider와 CI/CD 기능이 추가된다.

Plugin은 기능을 추가하거나 교체하기 위한 일정한 연결 규격이다.

```text
Generator Plugin
Validator Plugin
향후 Database Plugin
향후 Git Provider Plugin
```

Metadata는 Plugin의 이름, 버전, 기능과 필요한 권한을 설명한다.

## 12. Registry, Catalog, Loader

```text
Registry = ID로 Plugin을 찾는 보관함
Catalog  = AutoForge 기본 Plugin을 조립한 묶음
Loader   = 외부 폴더에서 Plugin Manifest를 발견하고 로딩
```

Catalog와 Loader를 분리한 이유는 AutoForge가 함께 배포하는 신뢰된 기본
기능과 사용자가 추가한 외부 코드를 같은 경로에서 자동 실행하지 않기 위해서다.

## 13. Pipeline과 EventBus

```text
Pipeline:
"명세 검사 후 생성하고, 검증 성공 후 Git 작업을 실행한다."

EventBus:
"생성이 끝났다"는 사건을 Logging과 Audit Handler에 전달한다.
```

Pipeline은 순서를 결정하고 EventBus는 사건을 알린다. 현재 전체 Pipeline
실행기는 아직 구현하지 않았다.

## 14. 현재와 미래

현재 완료:

- Project/Module 명세와 생성
- Router, Schema, Handler Scaffold
- 사용자 코드 보존
- Plan, Manifest, Workspace
- Import, pytest, Ruff, wheel 검증
- Generator/Validator Plugin과 Built-in Catalog

아직 없음:

- DatabaseSpec과 Repository 생성
- 전체 실행 Pipeline
- Git Commit/Push/PR 자동화
- Webhook과 CI/CD
- AI 생성

다음 단계는 DB 구현을 서두르기보다 DatabaseSpec과 Repository 파일
소유권을 먼저 정하는 것이다.

## 이번 권에서 기억할 것

```text
Specification은 입력을 검증한다.
Generator는 파일 내용을 메모리에서 만든다.
Plan은 예정표이고 Manifest는 영수증이다.
소유권과 Hash가 사용자 코드를 보호한다.
Validator가 생성 프로젝트의 실행 가능성을 확인한다.
Plugin은 기능 확장을 위한 연결 규격이다.
```

다음: [4권: 실제 코드 읽기](04_READING_AUTOFORGE_CODE.md)

