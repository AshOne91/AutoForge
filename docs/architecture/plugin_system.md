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
PluginLoader는 아직 구현되지 않았으며 Sample Plugin도 제공하지 않는다.

## 책임

- Plugin은 다른 Plugin을 직접 수정하지 않는다.
- PluginManager는 Plugin 등록, 조회와 실행을 담당한다.
- Plugin은 생성 규칙과 검증 기능을 확장할 수 있다.
- Generator Plugin은 Git에 직접 접근하지 않는다.
- 실행 순서와 실패 정책은 향후 Pipeline이 담당한다.

## 후속 구현

- Plugin ID와 API 버전
- Capability와 지원 명세 버전
- 의존성과 권한 검증
- PluginLoader
- Generator 및 Validator Plugin
- 격리와 실패 처리
