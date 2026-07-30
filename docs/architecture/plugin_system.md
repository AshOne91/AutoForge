# Plugin System

## 현재 구현

```text
Plugin
  → PluginManager
  → Registry
  → PluginContext
  → PluginResult
```

현재는 Plugin 기반 클래스, Metadata, Manager와 Registry만 구현되어 있다.
기존 Generator를 변경하지 않고 Metadata와 결합하는
`GeneratorPluginAdapter`가 구현되어 있다. PluginLoader는 아직 구현되지
않았으며 Sample Plugin도 제공하지 않는다.

Generator Plugin Metadata는 다음을 선언한다.

- Plugin 이름과 구현 Generator ID
- Plugin 버전과 구현 Generator 버전
- Plugin API 버전
- `generator` Capability
- 지원 Specification 버전

Adapter는 렌더링과 계획 전에 이 선언을 검증한다. 기존 범용
`Plugin.execute(context)` 계약은 호환성을 위해 유지하며 Generator에 억지로
적용하지 않는다.

## 책임

- Plugin은 다른 Plugin을 직접 수정하지 않는다.
- PluginManager는 Plugin 등록, 조회와 실행을 담당한다.
- Plugin은 생성 규칙과 검증 기능을 확장할 수 있다.
- Generator Plugin은 Git에 직접 접근하지 않는다.
- 실행 순서와 실패 정책은 향후 Pipeline이 담당한다.

## 후속 구현

- API 호환 버전 정책
- Plugin 의존성과 권한 검증
- PluginLoader
- Generator 및 Validator Plugin
- 격리와 실패 처리
