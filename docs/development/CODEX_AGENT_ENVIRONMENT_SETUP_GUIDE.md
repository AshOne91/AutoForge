# AutoForge Codex 개발환경 구축 가이드

> **목적**
> AutoForge를 처음 받는 개발자가 Windows + VS Code/Codex 환경에서 동일한 AI 개발환경을 재현할 수 있도록, 실제 구축 과정에서 검증한 설정·명령·문제 해결 경험을 한 문서에 정리한다.
>
> 이 문서는 “도구를 많이 붙이는 것”이 목적이 아니다.
> **최소 컨텍스트 → 필요한 도구만 호출 → 작은 테스트 → 작은 변경** 흐름을 고정해 Codex의 토큰/크레딧 낭비와 과잉 구현을 줄이는 것이 목적이다.

---

## 0. 최종 구성

최종적으로 AutoForge 개발환경은 다음 역할 분리를 사용한다.

```text
Codex
├─ AGENTS.md
│  └─ 항상 필요한 최소 규칙만
│
├─ Project Skills (.agents/skills)
│  ├─ model-routing
│  ├─ testing-workflow
│  ├─ autoforge-ownership
│  ├─ token-efficient-navigation
│  ├─ code-review-graph
│  └─ architecture-lineage
│
├─ Serena MCP
│  ├─ serena_autoforge
│  └─ serena_kis
│     → symbol / declaration / direct references / diagnostics
│
├─ CRG (code-review-graph) MCP
│  └─ graph / blast radius / review / multi-hop / cross-repo
│
└─ Ponytail
   └─ LITE
      → YAGNI / 과잉 추상화 / 불필요한 의존성 억제
```

핵심 원칙:

```text
정확한 symbol 찾기           → Serena
직접 reference 찾기          → Serena
구조적 관계 / blast radius   → CRG
실제 동작 증명               → pytest
생성 코드 소유권 판단        → autoforge-ownership
모델 비용/난이도 라우팅      → model-routing
과잉 구현 억제               → Ponytail LITE
과거 설계 계보 확인          → architecture-lineage
```

---

# 1. 검증된 환경

이 프로젝트에서 실제로 검증한 환경은 다음과 같다.

```text
OS                Windows
Python            3.12.13
Conda env          autoforge
uv                 0.12.2
uvx                0.12.2
Node.js            22.19.0
npm                10.9.3
Codex CLI           0.147.0
Ponytail            4.9.0 (검증 당시)
Serena              1.6.2.dev0 (검증 당시)
code-review-graph   2.3.7 (검증 당시)
```

버전은 시간이 지나면 달라질 수 있다.
**이 문서의 명령과 역할 분리를 기준으로 하고, 설치 버전은 현재 안정 버전을 사용한다.**

---

# 2. 프로젝트 역할

## AutoForge

기본 경로:

```text
C:\AutoForge
```

AutoForge는 **주 프로젝트**다.

주요 책임:

- specification
- generator
- plugin
- manifest / file ownership
- validation
- workspace
- Git automation
- reusable infrastructure contracts

## KIS consumer project

기본 경로:

```text
C:\kis-auto-trading
```

`kis-auto-trading`은 AutoForge의 **consumer / validation project**다.

중요 규칙:

```text
KIS에서 발견한 문제
        ↓
이 코드가 AutoForge generated-owned인가?
        ↓ yes
AutoForge generator/template/manifest 쪽을 수정
        ↓
다시 생성/검증
        ↓
KIS에서 확인
```

AutoForge가 소유한 generated 파일을 KIS에서 영구적으로 직접 패치하지 않는다.

---

# 3. 시작 전 Git 안전조치

이미 기능 작업 중이라면 AI 환경설정과 섞지 않는다.

예:

```powershell
cd C:\AutoForge

git status --short
git stash push -u -m "checkpoint: feature before codex tooling setup"

git switch -c chore/codex-cost-optimization
```

환경설정은 `chore/*` 브랜치에서 별도 커밋하고, 기능 WIP는 나중에 별도 `feat/*` 브랜치로 복원한다.

### PowerShell 주의

다음 명령은 PowerShell에서 잘못 해석될 수 있다.

```powershell
git stash apply stash@{0}
```

반드시 따옴표를 사용한다.

```powershell
git stash apply 'stash@{0}'
```

---

# 4. Codex CLI 설치

Codex CLI가 이미 있다면 건너뛴다.

공식 npm 방식:

```powershell
npm install -g @openai/codex
```

설치 확인:

```powershell
codex --version
Get-Command codex | Select-Object Name, Source, Version
```

프로젝트 루트에서 실행:

```powershell
cd C:\AutoForge
conda activate autoforge
codex
```

---

# 5. `~/.codex/config.toml`

사용자 전역 설정:

```text
C:\Users\<USER>\.codex\config.toml
```

이 파일은 프로젝트 Git에 커밋하지 않는다.

AutoForge/KIS에서 검증한 기본 구조:

```toml
service_tier = "default"
model = "gpt-5.6-luna"
model_reasoning_effort = "low"

[windows]
sandbox = "elevated"

[projects.'c:\autoforge']
trust_level = "trusted"

[projects.'c:\kis-auto-trading']
trust_level = "trusted"
```

## 모델 기본 정책

기본 라우팅:

```text
Luna → Terra → Sol
```

권장 의미:

```text
Luna / low     기본·탐색·기계적 작업
Luna / medium  일반 코드 변경
Terra          Luna로 부족하다는 증거가 있을 때
Sol            고난도 아키텍처/복합 디버깅의 hard gate
```

한 작업 도중 모델을 자주 바꾸지 않는다.

**복잡한 기술을 쓰는 프로젝트 = 항상 비싼 모델이 필요한 작업**은 아니다.

---

# 6. AGENTS.md 경량화

프로젝트 루트:

```text
C:\AutoForge\AGENTS.md
```

AGENTS.md에는 **항상 필요한 규칙만** 둔다.

넣어야 하는 것:

- AutoForge/KIS 역할
- 기본 코딩 규칙
- 좁은 탐색 순서
- focused test 정책
- Git safety
- 어떤 Skill을 언제 사용할지에 대한 포인터

넣지 말아야 하는 것:

- 모든 아키텍처 상세
- 모든 테스트 절차
- CRG 전체 사용법
- 과거 프로젝트 분석 전문
- 긴 roadmap

상세 절차는 `.agents/skills/`로 보낸다.

---

# 7. Project Skills

경로:

```text
C:\AutoForge\.agents\skills\
```

현재 권장 Skill:

```text
autoforge-ownership
architecture-lineage
code-review-graph
model-routing
testing-workflow
token-efficient-navigation
```

각 Skill은 다음 구조를 지켜야 한다.

```markdown
---
name: skill-name
description: When this skill should be used.
---

# Skill title
...
```

---

# 8. Windows에서 SKILL.md BOM 문제

실제 구축 과정에서 가장 중요한 문제 중 하나였다.

증상:

```text
Skipped loading skill(s) due to invalid SKILL.md files.
missing YAML frontmatter delimited by ---
```

파일을 열어 보면 첫 줄이 분명 `---`인데도 발생할 수 있다.

원인 후보:

```text
UTF-8 BOM
EF BB BF
```

Codex가 frontmatter의 시작을 정확히 `---`로 보지 못할 수 있다.

## 모든 Skill을 UTF-8 no BOM으로 다시 저장

```powershell
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

Get-ChildItem ".agents\skills\*\SKILL.md" | ForEach-Object {
    $text = [System.IO.File]::ReadAllText($_.FullName)
    [System.IO.File]::WriteAllText($_.FullName, $text, $utf8NoBom)
}
```

검증:

```powershell
Get-ChildItem ".agents\skills\*\SKILL.md" | ForEach-Object {
    $bytes = [System.IO.File]::ReadAllBytes($_.FullName)
    $first6 = ($bytes[0..5] | ForEach-Object { $_.ToString("X2") }) -join " "
    "{0,-90} {1}" -f $_.FullName, $first6
}
```

정상:

```text
2D 2D 2D
```

비정상 BOM 예:

```text
EF BB BF 2D 2D 2D
```

---

# 9. Serena MCP 설치

Serena는 exact symbol과 direct reference 탐색 담당이다.

먼저 확인:

```powershell
uv --version
uvx --version
```

## AutoForge Serena

`~/.codex/config.toml`:

```toml
[mcp_servers.serena_autoforge]
startup_timeout_sec = 15
command = "uvx"
args = [
    "--from",
    "git+https://github.com/oraios/serena",
    "serena",
    "start-mcp-server",
    "--project",
    'C:\AutoForge',
    "--context",
    "codex",
    "--open-web-dashboard",
    "False"
]
```

## KIS Serena

```toml
[mcp_servers.serena_kis]
startup_timeout_sec = 15
command = "uvx"
args = [
    "--from",
    "git+https://github.com/oraios/serena",
    "serena",
    "start-mcp-server",
    "--project",
    'C:\kis-auto-trading',
    "--context",
    "codex",
    "--open-web-dashboard",
    "False"
]
```

두 Serena 서버를 각각 repository에 pre-bind한다.

일반적인 repo-local 작업에서:

```text
activate_project
```

를 매번 호출하지 않는다.

---

# 10. Serena 프로젝트 파일 Git 정책

각 repository:

```text
.serena/
├─ .gitignore
├─ project.yml
├─ project.local.yml
├─ cache/
└─ memories/
```

`.serena/.gitignore`:

```gitignore
/cache
/project.local.yml
```

## Git에 포함

```text
.serena/.gitignore
.serena/project.yml
선별된 .serena/memories/*.md
```

## Git에서 제외

```text
.serena/cache/
.serena/project.local.yml
```

AutoForge에서 유지한 memory 예:

```text
.serena/memories/architecture/event_pipeline.md
.serena/memories/conventions.md
.serena/memories/core.md
.serena/memories/suggested_commands.md
.serena/memories/tech_stack.md
```

memory는 현재 TODO를 저장하는 장소가 아니다.

**오래 유지되는 프로젝트 사실과 규칙만 기록한다.**

---

# 11. Serena 실사용 검증

Codex에서 실제 tool surface를 사용한다.

AutoForge:

```text
mcp__serena_autoforge__find_symbol
target: PluginManager
```

검증된 위치 예:

```text
src/autoforge/core/plugin/manager.py
```

KIS:

```text
mcp__serena_kis__find_symbol
target: create_app
```

검증된 위치 예:

```text
src/kis_auto_trading/application/app_factory.py
```

설정 파일을 읽고 “될 것 같다”고 판단하지 않는다.

**실제 MCP tool call 성공을 최종 기준으로 한다.**

---

# 12. code-review-graph (CRG)

CRG는 repository graph 관계 담당이다.

Serena와 역할을 중복시키지 않는다.

```text
Serena
→ symbol
→ declaration
→ direct references
→ diagnostics

CRG
→ graph context
→ blast radius
→ review context
→ multi-hop
→ cross-repository relationships
```

설치 확인:

```powershell
uvx --from code-review-graph code-review-graph --help
```

---

# 13. CRG 설치 시 AutoForge 규칙 덮어쓰기 방지

CRG가 기존 AGENTS/Skills/hooks를 자동 변경하지 않도록 설치했다.

```powershell
uvx --from code-review-graph code-review-graph install `
    --repo "C:\AutoForge" `
    --platform codex `
    --no-skills `
    --no-hooks `
    --no-instructions
```

이 프로젝트에서는 이미 사람이 설계한:

```text
AGENTS.md
.agents/skills/
Ponytail hooks
```

가 있으므로 CRG가 이를 중복 생성하지 않도록 한다.

---

# 14. CRG multi-repo 등록

```powershell
code-review-graph register "C:\AutoForge" --alias autoforge
code-review-graph register "C:\kis-auto-trading" --alias kis
```

그래프 빌드:

```powershell
cd C:\AutoForge
code-review-graph build

cd C:\kis-auto-trading
code-review-graph build
```

CRG 데이터:

```text
.code-review-graph/
```

Git에는 넣지 않는다.

루트 `.gitignore`:

```gitignore
.code-review-graph/
```

---

# 15. CRG MCP 최소 tool surface

CRG의 모든 tool을 노출하지 않는다.

검증한 allowlist:

```text
get_minimal_context_tool
get_impact_radius_tool
get_review_context_tool
query_graph_tool
detect_changes_tool
traverse_graph_tool
cross_repo_search_tool
```

`~/.codex/config.toml`:

```toml
[mcp_servers.crg]
command = "uvx"
args = [
    "code-review-graph",
    "serve",
    "--tools",
    "get_minimal_context_tool,get_impact_radius_tool,get_review_context_tool,query_graph_tool,detect_changes_tool,traverse_graph_tool,cross_repo_search_tool"
]
cwd = "C:\AutoForge"
type = "stdio"
```

서버 이름은 이 프로젝트에서 다음으로 통일한다.

```text
crg
```

---

# 16. CRG deferred MCP 동작

실제 구축 중 다음 상황이 발생했다.

```text
/mcp UI
crg enabled
```

그런데 일반 callable MCP surface에서는:

```text
mcp__crg
없음
```

그러나 deferred `ALL_TOOLS`를 조회하자 다음 도구들이 실제 존재했다.

```text
mcp__crg__cross_repo_search_tool
mcp__crg__detect_changes_tool
mcp__crg__get_impact_radius_tool
mcp__crg__get_minimal_context_tool
mcp__crg__get_review_context_tool
mcp__crg__query_graph_tool
mcp__crg__traverse_graph_tool
```

그리고 실제 호출도 성공했다.

따라서:

```text
ordinary surface에 없음
≠
MCP가 고장남
```

CRG가 필요할 때는 deferred tool을 찾아 호출할 수 있다.

**단지 항상 보이게 하려고 MCP deferral을 끄지 않는다.**

항상 tool schema를 노출하면 오히려 기본 컨텍스트가 커질 수 있다.

---

# 17. CRG tool 선택 규칙

## `query_graph_tool`

symbol 관계 확인.

CRG qualified target을 우선한다.

```text
relative/path.py::Class.method
```

예:

```text
src/autoforge/core/plugin/manager.py::PluginManager.execute
```

bare symbol:

```text
PluginManager.execute
```

만 전달했을 때 `not_found`가 발생한 경험이 있으므로 정확한 path-qualified target을 사용한다.

## `get_impact_radius_tool`

이 도구는 **파일 단위**다.

잘못된 예:

```text
changed_files:
PluginManager.execute
```

올바른 예:

```text
changed_files:
src/autoforge/core/plugin/manager.py
```

## `traverse_graph_tool`

direct reference보다 더 넓은 multi-hop 관계가 실제로 필요할 때만 사용한다.

## `detect_changes_tool`

현재 diff의 구조적 영향을 확인할 때 사용한다.

## `cross_repo_search_tool`

AutoForge ↔ KIS 관계가 실제로 필요한 경우만 사용한다.

---

# 18. CRG와 Serena를 같이 쓰는 패턴

예:

```text
질문:
PluginManager.execute 변경 영향은?
```

순서:

```text
Serena
→ PluginManager.execute 정확한 파일 위치 확인

CRG
→ path::Class.method 로 graph 관계 확인

필요 시
→ traverse_graph

검증
→ focused pytest
```

동일한 단순 질문을 Serena와 CRG 둘 다에 중복 요청하지 않는다.

---

# 19. Ponytail 설치

Ponytail은 과잉 구현을 억제하는 보조 레이어다.

Node/npm 확인:

```powershell
node --version
npm --version
```

Codex plugin marketplace 등록:

```powershell
codex plugin marketplace add DietrichGebert/ponytail
```

확인:

```powershell
codex plugin marketplace list
```

설치:

```powershell
codex plugin add ponytail@ponytail
```

확인:

```powershell
codex plugin list
```

---

# 20. Ponytail hooks 검토

Codex CLI 실행:

```powershell
codex
```

안에서:

```text
/hooks
```

**Trust all을 바로 누르지 말고 먼저 Review hooks를 확인한다.**

검증한 Ponytail 4.9.0에서는 다음 3개 hook이 나타났다.

```text
SessionStart
UserPromptSubmit
SubagentStart
```

최종 정상 상태:

```text
Event              Installed   Active
SessionStart       1           1
UserPromptSubmit   1           1
SubagentStart      1           1
```

hook command가 실제 설치된 Ponytail plugin 경로의 Node script를 가리키는지 확인한 뒤 trust한다.

---

# 21. Ponytail을 LITE로 고정

Ponytail 기본 동작이 AutoForge의 기존 architecture/testing/ownership 규칙보다 강하게 개입하지 않도록 `lite`를 사용한다.

Windows config:

```text
%APPDATA%\ponytail\config.json
```

PowerShell:

```powershell
$configDir = Join-Path $env:APPDATA "ponytail"
$configFile = Join-Path $configDir "config.json"

New-Item -ItemType Directory -Force $configDir | Out-Null

@'
{
  "defaultMode": "lite"
}
'@ | Set-Content -Encoding utf8 $configFile
```

확인:

```powershell
Get-Content $configFile -Raw
```

Codex CLI 새 세션:

```text
@ponytail
```

검증된 정상 출력:

```text
PONYTAIL:LITE
PONYTAIL MODE ACTIVE — level: lite
```

---

# 22. Ponytail의 역할 한계

Ponytail이 최상위 설계 권한을 갖는 것은 아니다.

우선순위:

```text
correctness
→ ownership
→ contracts
→ tests
→ security/data safety
→ Ponytail minimization
```

Ponytail 때문에:

- 필요한 abstraction을 삭제하거나
- generated ownership을 깨뜨리거나
- 테스트를 생략하거나
- architecture contract를 우회하면 안 된다.

Ponytail의 주 역할:

```text
YAGNI
불필요한 dependency
불필요한 abstraction
불필요한 future architecture
불필요한 boilerplate
```

---

# 23. Architecture Lineage

과거 설계 계보는 중요하지만 항상 컨텍스트에 넣지 않는다.

Skill:

```text
C:\AutoForge\.agents\skills\architecture-lineage\SKILL.md
```

원본/reference 경로:

```text
common-tool
C:\게임베이스툴\common-tool-master

game-server
C:\게임베이스서버\game-server-master

base_server
C:\SKN12-FINAL-2TEAM\base_server
```

현재 AutoForge 요약 분석본:

```text
C:\AutoForge\docs\architecture\common_tool_analysis.md
```

현재 KIS:

```text
C:\kis-auto-trading
```

참조 우선순위:

```text
1. Current AutoForge contracts/tests
2. Current KIS vertical slice
3. common-tool generation intent
4. game-server runtime meaning
5. base_server Python/FastAPI reference
```

historical code를 그대로 포팅하지 않는다.

---

# 24. `.codex` 문서 경량화

최종적으로 `.codex`는 다음 정도만 유지한다.

```text
.codex/
├─ architecture.md
├─ current_status.md
├─ next_task.md
├─ project_context.md
└─ roadmap.md
```

삭제/통합한 과거 중복 파일 예:

```text
bootstrap.md
coding_style.md
common_tool_analysis.md
development_rules.md
```

이유:

- AGENTS와 중복
- Skills와 중복
- `docs/architecture/`와 중복
- 오래된 상태 정보
- 매 작업마다 읽으면 토큰 낭비

`.codex`는 reference material이다.

**모든 `.codex` 파일을 매 작업 시작 시 읽지 않는다.**

---

# 25. 통합 MCP sanity check

설정이 끝났으면 `codex`에서 실제 호출을 검증한다.

예시 prompt:

```text
현재 환경의 통합 tool sanity check를 수행해.

코드나 파일은 수정하지 마.

1. Serena AutoForge:
   mcp__serena_autoforge__find_symbol 을 실제 호출해서
   PluginManager 를 찾아라.

2. Serena KIS:
   mcp__serena_kis__find_symbol 을 실제 호출해서
   create_app 을 찾아라.

3. CRG:
   mcp__crg__get_minimal_context_tool 을 실제 호출해서
   C:\AutoForge 에서
   "PluginManager 구조를 이해하기 위한 최소 컨텍스트"
   를 요청해라.

CRG가 deferred라면 ALL_TOOLS에서 찾아서 호출해.

마지막에는 success/fail만 보고해.
코드를 수정하지 마.
```

검증된 정상 결과:

```text
Serena AutoForge  success
Serena KIS        success
CRG               success
code modified      no
```

---

# 26. `MCP startup interrupted` 대응

실제 Codex CLI 시작 시:

```text
MCP startup interrupted.
servers were not initialized:
codex_apps, crg, serena_autoforge, serena_kis
```

가 표시된 경험이 있다.

**이 메시지만 보고 설정을 변경하지 않는다.**

먼저:

```text
/mcp
```

를 확인한다.

정상이라면:

```text
crg
→ tool list 표시

serena_autoforge
→ tool list 표시

serena_kis
→ tool list 표시
```

그 다음 실제 tool call을 수행한다.

실제 호출이 성공하면 startup banner보다 **실제 callable result가 더 강한 증거**다.

---

# 27. Serena 15초 timeout 경고

다음 경고도 발생할 수 있었다.

```text
MCP client for serena_autoforge timed out after 15 seconds
MCP client for serena_kis timed out after 15 seconds
```

처리 순서:

```text
1. /mcp 확인
2. 실제 Serena tool 호출
3. 성공하면 즉시 timeout 값을 올리지 않음
4. 실제 호출도 실패할 때만 startup_timeout_sec 증가 검토
```

경고를 없애는 것이 목적이 아니다.

**실제 개발 도구가 동작하는 것이 목적이다.**

---

# 28. `/mcp`의 `Auth: Unsupported`

local stdio MCP에서 다음처럼 보일 수 있다.

```text
crg
Auth: Unsupported

serena_autoforge
Auth: Unsupported
```

우리 검증에서는 이것이 tool failure를 의미하지 않았다.

판정 기준:

```text
Tools가 보이는가?
실제 tool call이 성공하는가?
```

이다.

---

# 29. pytest cache warning

focused tests에서 다음 경고가 발생한 적이 있다.

```text
PytestCacheWarning
cache could not write path .pytest_cache
Permission denied
```

그러나:

```text
44 passed
```

였다.

이 경우:

```text
test failure
```

로 분류하지 않는다.

필요 시 `.pytest_cache`를 삭제하거나 권한을 정리하되, 기능 작업과 무관하면 별도 cleanup으로 분리한다.

---

# 30. CRLF → LF 경고

Git에서:

```text
CRLF will be replaced by LF the next time Git touches it
```

가 발생할 수 있다.

`git diff --check`가 깨끗하다면 이것만으로 작업을 중단하지 않는다.

---

# 31. 이상한 `tash push ...` 파일

PowerShell 명령 입력 실수로 다음과 같은 untracked file이 만들어진 경험이 있다.

```text
tash push -u -m checkpoing...
```

내용은 단순 git diff stat이었다.

삭제:

```powershell
Get-ChildItem -LiteralPath . -Force -File |
Where-Object { $_.Name -like "tash push*" } |
Remove-Item -Force
```

그 뒤:

```powershell
git status --short
```

로 확인한다.

---

# 32. Git에 넣는 것 / 넣지 않는 것

## Commit

```text
AGENTS.md
.agents/skills/*
.serena/.gitignore
.serena/project.yml
선별된 .serena/memories/*
.codex의 경량 reference docs
docs/*
.gitignore
```

## Local only

```text
~/.codex/config.toml
%APPDATA%\ponytail\config.json
.serena/cache/
.serena/project.local.yml
.code-review-graph/
.pytest_cache/
.ruff_cache/
.env
credentials
```

---

# 33. KIS tooling setup

KIS에도 최소 Serena metadata와 ignore를 둔다.

예:

```text
C:\kis-auto-trading\.serena\.gitignore
C:\kis-auto-trading\.serena\project.yml
```

`.gitignore` 권장:

```gitignore
.pytest_cache/
.ruff_cache/
.code-review-graph/
```

KIS에서 tooling만 변경했다면 기능 branch를 만들 필요 없이 별도 tooling commit으로 `main`에 넣을 수 있다.

예:

```powershell
git add .gitignore .serena/.gitignore .serena/project.yml
git diff --cached --check
git commit -m "chore: add Codex navigation tooling"
```

---

# 34. AutoForge tooling Git workflow

권장 흐름:

```text
main
  ↓
chore/codex-cost-optimization
  ├─ AGENTS/Skills/Serena/CRG
  ├─ .codex cleanup
  └─ architecture-lineage
  ↓
main merge
  ↓
feat/actual-feature
```

환경설정과 기능 구현을 같은 commit에 섞지 않는다.

---

# 35. 신규 개발자 Quick Setup

새 개발자는 아래 순서로 진행하면 된다.

## STEP 1

Repository 준비:

```powershell
cd C:\AutoForge
conda activate autoforge
git status
```

## STEP 2

도구 확인:

```powershell
python --version
uv --version
uvx --version
node --version
npm --version
codex --version
```

## STEP 3

`~/.codex/config.toml`에:

```text
AutoForge Serena
KIS Serena
CRG
```

등록.

## STEP 4

Codex 실행:

```powershell
codex
```

## STEP 5

```text
/mcp
```

에서:

```text
crg
serena_autoforge
serena_kis
```

확인.

## STEP 6

Ponytail 설치:

```powershell
codex plugin marketplace add DietrichGebert/ponytail
codex plugin add ponytail@ponytail
```

## STEP 7

```text
/hooks
```

에서 hook 내용을 검토하고 trust.

## STEP 8

`%APPDATA%\ponytail\config.json`:

```json
{
  "defaultMode": "lite"
}
```

## STEP 9

새 Codex session:

```text
@ponytail
```

`PONYTAIL:LITE` 확인.

## STEP 10

통합 Serena + CRG sanity test 수행.

여기까지 통과하면 개발을 시작한다.

---

# 36. 실제 개발 기본 prompt

새 작업을 시작할 때 매번 거대한 master prompt를 넣을 필요가 없다.

예:

```text
현재 AutoForge 작업을 이어간다.

AGENTS.md와 관련 Skill만 적용해.

탐색:
- exact symbol/direct refs → Serena
- graph/blast radius → 필요할 때만 CRG
- repo 전체 scan 금지

Ponytail LITE 원칙을 유지하고
과잉 추상화나 unrelated refactoring을 하지 마.

먼저 현재 변경사항을 보존하고
다음 최소 구현 단위 1개를 진행해.

검증:
focused test
→ affected tests
→ 더 넓은 테스트는 위험이 있을 때만
```

---

# 37. Model routing 보고 예

중요 코드 작업에서는 `model-routing` Skill을 사용한다.

예:

```text
[MODEL ROUTING]
Current: GPT-5.6 Luna / low
Decision: KEEP
Reason:
- bounded implementation
- exact contracts already exist
- Serena can locate symbols
- focused tests provide proof
Escalation gate:
- conflicting architecture evidence
- repeated failed attempts
- multi-module semantic ambiguity
```

“복잡해 보인다”만으로 Terra/Sol로 올리지 않는다.

---

# 38. Tool 선택 치트시트

| 질문 | 도구 |
|---|---|
| 이 클래스 어디 있지? | Serena |
| 이 메서드를 누가 직접 참조하지? | Serena |
| 파일 하나 바꾸면 구조적으로 어디까지 영향이지? | CRG impact |
| 특정 symbol의 graph caller는? | CRG query graph |
| 몇 hop 뒤까지 이어지지? | CRG traverse |
| 현재 diff의 구조적 위험은? | CRG detect/review |
| AutoForge ↔ KIS 연관은? | CRG cross-repo |
| 테스트가 진짜 통과하나? | pytest |
| 이 generated 파일 어디서 고쳐야 하나? | autoforge-ownership |
| 과도한 구현 아닌가? | Ponytail |
| common-tool 설계 의도는? | architecture-lineage |

---

# 39. Context economy 체크리스트

작업 전:

```text
[ ] 현재 request/error만 본다
[ ] 필요한 symbol부터 찾는다
[ ] 이미 context에 있는 정보를 다시 읽지 않는다
[ ] 모든 .codex 문서를 읽지 않는다
[ ] 모든 Serena memory를 읽지 않는다
[ ] CRG를 symbol lookup 대용으로 쓰지 않는다
[ ] 전체 pytest부터 돌리지 않는다
[ ] historical repo를 무조건 스캔하지 않는다
```

작업 후:

```text
[ ] focused test
[ ] 변경 파일 보고
[ ] 미실행 검사 보고
[ ] 필요 없는 abstraction 추가 여부 확인
[ ] generated ownership 위반 여부 확인
```

---

# 40. 초기 구축 중 실제로 배운 것

## 1. “enabled”와 “callable”을 구분한다

UI에 MCP가 enabled라고 나오는 것과 agent가 실제 tool call 가능한 것은 다르다.

최종 기준은:

```text
실제 call success
```

다.

## 2. tool surface가 안 보여도 deferred일 수 있다

CRG가 ordinary surface에서 보이지 않았지만 `ALL_TOOLS`에서 발견되고 실제 호출됐다.

## 3. schema를 확인하지 않고 도구를 쓰면 정상 결과가 오히려 오해를 만든다

`get_impact_radius_tool`에 symbol을 넣었더니 정상 `status: ok`인데 impact가 0이었다.

도구가 실패한 것이 아니라 **잘못된 인자 의미로 정상 실행**된 것이다.

## 4. bare symbol보다 graph-qualified target이 중요할 수 있다

```text
PluginManager.execute
```

는 `not_found`.

```text
src/autoforge/core/plugin/manager.py::PluginManager.execute
```

는 성공했다.

## 5. 경고가 곧 장애는 아니다

Serena timeout이나 MCP startup interrupted가 떠도 `/mcp`와 실제 call은 정상이었다.

## 6. Skills도 토큰 최적화 대상이다

모든 규칙을 AGENTS.md에 몰아넣지 않는다.

필요할 때만 Skill 본문을 로드하도록 분리한다.

## 7. reference architecture는 삭제가 아니라 on-demand화한다

common-tool / game-server / base_server 지식은 중요하지만 항상 prompt에 넣지 않는다.

`architecture-lineage` Skill로 필요할 때만 접근한다.

## 8. AI 환경설정도 기능 개발과 Git history를 분리한다

tooling commit과 feature commit을 섞지 않는다.

---

# 41. Maintenance

도구 업데이트 후 확인해야 하는 것:

```text
Codex CLI
Serena
CRG
Ponytail
```

업데이트했다고 바로 프로젝트 규칙을 다시 만들 필요는 없다.

먼저:

```text
1. version 확인
2. /mcp 확인
3. hooks 확인
4. sanity call
5. 기존 Skill 동작 확인
```

순서로 회귀 여부를 판단한다.

CRG graph는 코드가 크게 변경되면 incremental update/rebuild를 수행한다.

매 edit마다 전체 graph를 rebuild하지 않는다.

---

# 42. 최종 완료 기준

다음이 전부 맞으면 환경 구축 완료다.

```text
[ ] Codex CLI 실행
[ ] AutoForge/KIS trusted
[ ] AGENTS.md 경량화
[ ] project Skills 로드
[ ] 모든 SKILL.md UTF-8 no BOM
[ ] Serena AutoForge 실제 call 성공
[ ] Serena KIS 실제 call 성공
[ ] CRG 실제 call 성공
[ ] CRG 7-tool allowlist
[ ] Ponytail plugin enabled
[ ] Ponytail hooks trusted/active
[ ] Ponytail LITE 확인
[ ] .serena cache/local config ignore
[ ] .code-review-graph ignore
[ ] .codex reference 문서 경량화
[ ] architecture-lineage reference paths 등록
[ ] tooling commit과 feature commit 분리
```

---

# 43. 프로젝트용 최종 원칙

```text
Serena for precision.
CRG for relationships.
Tests for proof.
Ownership before editing generated code.
Ponytail for restraint.
Skills only when relevant.
Historical references only when architecture actually needs them.
```

이 문서의 목적은 AI에게 저장소 전체를 더 많이 읽게 하는 것이 아니다.

**더 적게 읽고, 더 정확하게 찾고, 더 작은 단위로 수정하고, 테스트로 증명하게 만드는 것**이 최종 목적이다.
