# Plugin System

## 계약

```text
Plugin
  → PluginManager
  → Registry
  → PluginContext
  → PluginResult
```

Plugin 기반 클래스, Metadata, Manager, Registry, Generator Adapter와 Loader가
각자의 경계를 가진다. `GeneratorPluginAdapter`는 기존 Generator를 변경하지
않고 Metadata와 결합한다. PluginLoader는 지정된 루트 바로
아래의 `plugin.json`을 결정적인 순서로 발견하고 Metadata를 검증한다.
발견 단계에서는 Plugin Python 코드를 Import하거나 실행하지 않는다.

Generator Plugin Metadata는 다음을 선언한다.

- Plugin 이름과 구현 Generator ID
- Plugin 버전과 구현 Generator 버전
- Plugin API 버전
- `generator` Capability
- 지원 Specification 버전
- 버전이 있는 Plugin 의존성
- 파일 읽기·쓰기, Process 실행과 Network 접근 권한

Adapter는 렌더링과 계획 전에 이 선언을 검증한다. 기존 범용
`Plugin.execute(context)` 계약은 호환성을 위해 유지하며 Generator에 억지로
적용하지 않는다.

지원하는 Plugin API 버전은 `1`이다. Capability는 Plugin이 제공하는
기능이고 Permission은 Plugin 실행에 필요한 외부 자원 접근 권한이다.
두 개념을 섞지 않는다.

기존 `dependencies: list[str]`는 공개 API 호환성을 위해 유지한다. 새 Plugin은
`PluginDependency(plugin_id, required_version)`로 정확한 의존 버전을
선언한다. 자기 의존, 중복 의존성과 중복 권한은 Metadata 생성 시 거부한다.

PluginLoader는 발견된 전체 후보에서 기존 문자열 의존성과 버전형 의존성을
함께 해석한다. 누락된 Plugin, 정확한 버전 불일치와 순환 의존성을 거부하고
의존 Plugin이 먼저 오는 결정적인 순서를 반환한다. 이 과정도 Plugin 코드를
실행하지 않는다.

`load_trusted()`는 발견·정렬과 분리된 명시적 실행 경계다. `module:factory`
Entrypoint의 경로를 다시 검증하고 Factory가 `Plugin`을 반환하는지, 런타임
Metadata가 Manifest와 완전히 일치하는지 확인한다. 모든 Factory가 성공한
뒤에만 의존성 순서로 PluginManager에 등록하며 중간 등록 실패는 이번 호출의
등록분을 Rollback한다.

Permission은 선언과 중복 검증을 제공한다. `load_trusted()`는 신뢰한 로컬
Plugin을 위한 API이며 OS 수준 Sandbox를 제공하지 않는다.

`GeneratorPluginRegistry[SpecificationT]`는 기존 범용 Registry를 조합해
Generator ID 기반 등록·조회·목록을 제공한다. ProjectSpec과 ModuleSpec
Registry를 분리하므로 호출 시 명세 타입이 유지된다. FastAPI Project와
Module Generator는 각각 Metadata와 결합되어 실제 Registry에 등록된다.

`ValidatorPluginRegistry[RequestT, ResultT]`는 비동기 Validator의 요청과 결과
타입을 함께 보존한다. ProjectValidator는 별도 Request Adapter를 통해
Import, pytest, Ruff와 wheel Build를 그대로 실행한다. Metadata에는 파일
읽기·쓰기와 Process 실행 권한을 선언한다.

`BuiltinPluginCatalog`는 FastAPI Project/Module Generator Registry와
Project Validator Registry를 하나의 불변 조립 결과로 제공한다. 생성할
package name, ProcessRunner, Python 실행 경로와 Timeout은 Catalog 생성 시
명시적으로 주입하며 전역 Catalog나 공유 Registry를 만들지 않는다.

Built-in Catalog는 AutoForge가 함께 배포하는 구현을 조립하는 책임만 가진다.
PluginLoader는 외부 디렉터리의 Manifest 발견, 의존성 정렬과 명시적인 trusted
로딩을 담당하므로 두 경로는 서로 대체하거나 자동으로 연결되지 않는다.

## 책임

- Plugin은 다른 Plugin을 직접 수정하지 않는다.
- PluginManager는 Plugin 등록, 조회와 실행을 담당한다.
- Plugin은 생성 규칙과 검증 기능을 확장할 수 있다.
- Generator Plugin은 Git에 직접 접근하지 않는다.
- 실행 순서와 실패 정책은 Pipeline이 담당한다.
