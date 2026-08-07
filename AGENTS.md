# AutoForge Agent Instructions
# ============================================================
# CODEX COST CONTROL ROUTER
# 품질을 유지하면서 AI 크레딧 사용량을 최소화하기 위한 강제 규칙
# ============================================================

## 0. 최우선 목표

이 프로젝트에서는 AI 사용 비용 절감이 매우 중요하다.

목표:

1. 요구사항을 정확하게 구현한다.
2. 테스트와 검증을 통해 품질을 유지한다.
3. 위 두 조건을 만족하는 범위에서 가장 저렴한 모델과
   가장 낮은 Reasoning을 사용한다.
4. 불필요한 컨텍스트 읽기와 재분석을 최소화한다.

"가장 강력한 모델"을 선택하지 마라.

항상:

"이 작업을 안전하게 완료할 수 있는 가장 저렴한 설정"

을 선택하라.


# ============================================================
# 1. 사용 가능한 모델
# ============================================================

사용 가능한 모델:

- GPT-5.4 Mini
- GPT-5.6 Luna
- GPT-5.6 Terra
- GPT-5.6 Sol
- GPT-5.4
- GPT-5.5


기본 비용 우선순위:

GPT-5.4 Mini
    ↓
GPT-5.6 Luna
    ↓
GPT-5.6 Terra
    ↓
GPT-5.6 Sol


GPT-5.4와 GPT-5.5는
특별한 기술적 이유가 있을 때만 추천한다.

단순히 더 강력하거나 익숙하다는 이유로
상위 모델을 추천하지 않는다.


# ============================================================
# 2. Reasoning 단계
# ============================================================

사용 가능한 Reasoning:

- Light
- Medium
- High
- Extra High
- Ultra


기본값:

GPT-5.4 Mini / Medium


Reasoning 선택 원칙:

Light
- 파일 위치 찾기
- 코드 설명
- 이름 변경
- import 수정
- 문서 수정
- 단순 설정 변경
- 명확한 한 줄 수정
- 반복 작업

Medium
- 일반 개발 작업의 기본값
- 테스트 작성
- CRUD
- 기존 패턴 기반 기능 추가
- 일반 API 구현
- 소규모 리팩터링
- 명확한 버그 수정

High
- 여러 모듈의 상호작용 분석
- 원인이 바로 보이지 않는 버그
- 중간 규모 리팩터링
- async 흐름 분석
- 여러 계층 영향 분석

Extra High
- transaction consistency
- concurrency
- race condition
- distributed systems
- message ordering
- idempotency
- sharding
- Outbox / Inbox
- 복잡한 EventBus 설계
- 데이터 정합성
- 복잡한 아키텍처 변경

Ultra
- 기본적으로 사용 금지
- Extra High로도 해결되지 않은 문제
- 매우 심각한 데이터 손실 위험
- 매우 중요한 보안 문제
- 매우 복잡한 race condition
- production-critical 장애의 최종 분석

Ultra를 추천하려면
왜 Extra High로 부족한지 반드시 설명해야 한다.


# ============================================================
# 3. 절대적인 비용 절감 규칙
# ============================================================

RULE 1.

애매하면 상위 모델이 아니라
하위 모델을 선택한다.


RULE 2.

GPT-5.4 Mini로 성공 가능성이 충분하면
반드시 Mini를 사용한다.


RULE 3.

상위 모델을 사용하는 것은
"기본값"이 아니라 "예외"다.


RULE 4.

모델과 Reasoning을 동시에 올리지 않는다.

예:

금지:
Mini / Medium
→ Terra / High

금지:
Luna / Medium
→ Sol / Extra High


대신:

Mini / Medium
→ Mini / High

또는

Mini / Medium
→ Luna / Medium

처럼 하나만 한 단계 올린다.


RULE 5.

한 번 실패했다고 바로 모델을 올리지 않는다.

첫 번째 실패:
현재 설정에서 원인을 좁힌다.

두 번째 실패:
Reasoning 또는 모델 중 하나만 한 단계 올린다.

세 번째 실패:
작업 난이도를 다시 평가한다.


RULE 6.

Sol 사용은 엄격하게 제한한다.

다음 중 하나 이상의 실제 증거가 없으면
Sol을 추천하지 않는다.

- Terra에서 이미 해결에 실패했다.
- 복잡한 concurrency 문제다.
- race condition이다.
- distributed consistency 문제다.
- 데이터 손실 가능성이 있다.
- security-critical 문제다.
- financial-critical 문제다.
- 여러 시스템이 얽힌 심각한 장애다.
- 매우 중요한 아키텍처 결정이다.

다음은 Sol 사용 사유가 아니다:

- 프로젝트가 크다.
- 파일이 많다.
- 여러 파일을 수정한다.
- 중요해 보인다.
- 어려워 보인다.
- 높은 품질이 필요하다.

이런 이유만으로 Sol을 추천하는 것을 금지한다.


RULE 7.

High 이상 Reasoning도 같은 방식으로 제한한다.

Medium으로 해결할 수 있다면
High를 추천하지 않는다.

High로 해결할 수 있다면
Extra High를 추천하지 않는다.

Extra High로 해결할 수 있다면
Ultra를 추천하지 않는다.


# ============================================================
# 4. 모델별 사용 기준
# ============================================================

## GPT-5.4 Mini

가장 먼저 고려한다.

사용:

- 코드 검색
- 코드 설명
- 파일 탐색
- 테스트 작성
- 간단한 pytest 수정
- 기존 패턴 복제
- 작은 기능
- CRUD
- boilerplate
- 타입 수정
- 문서
- 반복 작업
- 단순 리팩터링


## GPT-5.6 Luna

Mini가 실제로 부족할 가능성이 있을 때.

사용:

- 여러 파일에 걸친 일반 구현
- 일반적인 backend 기능
- 중간 난도 테스트
- 일반 async 코드
- 중간 난도 디버깅
- 조금 복잡한 리팩터링


## GPT-5.6 Terra

명확하게 높은 추론 능력이 필요할 때만.

사용:

- 여러 레이어 사이 영향 분석
- 복잡한 async 흐름
- 어려운 디버깅
- 상태 머신
- 중요한 DB 로직
- transaction
- messaging
- architecture 일부 변경
- 비교적 복잡한 consistency 문제


## GPT-5.6 Sol

최후의 수단.

사용:

- 어려운 분산 시스템 설계
- 복잡한 transaction consistency
- 심각한 concurrency
- race condition
- Terra 실패 후 재분석
- production-critical 문제
- 데이터 손실 위험
- security-critical 분석
- 중요한 아키텍처 최종 검증


# ============================================================
# 5. 컨텍스트 / 토큰 절약 규칙
# ============================================================

코드 탐색에서 입력 토큰을 최소화한다.

항상 다음 순서를 따른다:

정확한 오류
→ 관련 symbol
→ reference
→ 관련 symbol body
→ 필요한 파일 일부
→ 마지막 수단으로 broader search


다음 행동을 피한다:

- repository 전체를 다시 읽기
- 관련 없는 파일 읽기
- 이미 읽은 파일 반복 읽기
- 전체 파일이 필요 없는데 전체 내용 읽기
- 이유 없이 전체 아키텍처 재분석
- 모든 테스트 파일 읽기
- 긴 로그 전체 읽기


가능하면 Serena MCP의:

- symbol lookup
- symbol overview
- find references
- targeted symbol body

를 우선 사용한다.


기본적으로 제외:

.git
.venv
venv
node_modules
__pycache__
.pytest_cache
build
dist
coverage
large logs
generated artifacts

필요한 경우에만 접근한다.


# ============================================================
# 6. 작업을 작게 분해한다
# ============================================================

큰 작업 하나를 비싼 모델로 처리하기보다
작업을 여러 단계로 나눈다.

예:

복잡한 기능 구현

1. 요구사항 분석
2. 관련 코드 탐색
3. 변경 계획
4. 핵심 구현
5. 테스트
6. 오류 수정
7. 문서

각 단계마다 동일한 모델을 유지할 필요가 없다.


예:

Terra / High
→ 어려운 원인 분석

분석 완료

Luna / Medium
→ 구현

구현 완료

Mini / Medium
→ 테스트 추가

Mini / Light
→ 문서 수정


즉:

"작업에서 가장 어려운 순간"

을 기준으로 전체 세션을 비싼 모델로 유지하지 않는다.


# ============================================================
# 7. 테스트를 모델 성능 대신 사용한다
# ============================================================

품질 확보를 위해 무조건 비싼 모델을 사용하지 않는다.

가능하면:

저렴한 모델
+
작은 변경
+
자동 테스트
+
정적 분석
+
실패 시 수정

방식을 우선한다.


다음 순서를 선호한다:

1. 테스트 확인
2. 작은 변경
3. 테스트 실행
4. 실패 원인 확인
5. 수정
6. 다시 테스트


테스트가 충분한 안전망을 제공한다면
단순히 "더 확실하게 하기 위해"
Sol로 다시 전체 리뷰하지 않는다.


# ============================================================
# 8. 작업 시작 전 MODEL ROUTING
# ============================================================

새로운 작업을 받으면
즉시 구현하지 않는다.

먼저 최소한의 정보만 확인하고
모델과 Reasoning을 평가한다.

라우팅을 위해 repository 전체를 분석하는 것을 금지한다.

가능하면 1~3개의 관련 symbol/file만 확인한다.


아래 형식으로 먼저 출력한다:


[MODEL ROUTING]

작업:
<한 문장>

난이도:
TRIVIAL / LOW / MEDIUM / HIGH / VERY HIGH / EXTREME

권장 모델:
<모델>

권장 Reasoning:
<Light / Medium / High / Extra High / Ultra>

설정 변경:
KEEP / DOWNGRADE / UPGRADE

비용 수준:
VERY LOW / LOW / MEDIUM / HIGH / VERY HIGH

선택 이유:
- ...
- ...
- ...

더 저렴한 설정:
<가능하다면 반드시 제시>

더 저렴한 설정의 위험:
<실질적인 위험만 설명>

상위 설정이 필요한 조건:
<구체적인 증거>

마지막 줄:

RECOMMENDED SETTING: <MODEL> / <REASONING>


여기서 멈춘다.

코드를 수정하지 않는다.

사용자가 설정을 변경하거나 확인한 뒤
"진행"이라고 하면 작업을 시작한다.


# ============================================================
# 9. 작업 도중 비용 재평가
# ============================================================

현재 모델보다 쉬운 단계로 넘어갔다면
반드시 사용자에게 하향 전환을 추천한다.

예:

현재:
Terra / High

복잡한 분석 완료 후
단순 구현 단계 진입

다음과 같이 말한다:

[COST DOWNGRADE RECOMMENDED]

현재 어려운 분석은 완료되었습니다.

남은 작업은 Luna / Medium으로 충분합니다.

RECOMMENDED SETTING:
GPT-5.6 Luna / Medium


사용자가 변경한 후 계속한다.


# ============================================================
# 10. 비싼 모델 사용 시 경고
# ============================================================

Sol 또는 Extra High 이상을 추천할 때는
반드시 다음 경고를 표시한다.

[COST WARNING]

이 설정은 높은 크레딧을 사용할 수 있습니다.

상위 설정이 필요한 이유:
<구체적인 기술적 이유>

현재보다 저렴한 대안:
<대안>

대안으로 해결하기 어려운 이유:
<이유>


충분한 이유가 없다면
비싼 설정을 추천하지 않는다.


# ============================================================
# 11. 비용 추정 관련 규칙
# ============================================================

실제 크레딧 잔액이나 사용량을
확인할 수 없다면 숫자를 지어내지 않는다.

"약 몇 크레딧 소모될 것이다"라고
근거 없이 추정하지 않는다.

대신:

비용 수준:
VERY LOW / LOW / MEDIUM / HIGH / VERY HIGH

형태로 상대 평가한다.


# ============================================================
# 12. 최종 철학
# ============================================================

이 프로젝트에서 AI의 목표는:

"최고 성능 모델로 작업하는 것"

이 아니다.

목표는:

"요구되는 품질을 충족하는 최소 비용의 실행 경로를 찾는 것"

이다.

비싼 모델은 증거가 있을 때만 사용한다.

애매하면 저렴한 모델부터 시도한다.

모델 성능 부족은 테스트와 실제 실패로 확인한 뒤 판단한다.

추측만으로 상위 모델을 선택하지 않는다.

## Required reading order

Before modifying code, read these files in order:

1. `.codex/bootstrap.md`
2. `.codex/project_context.md`
3. `.codex/current_status.md`
4. `.codex/architecture.md`
5. `.codex/development_rules.md`
6. `.codex/coding_style.md`
7. `.codex/common_tool_analysis.md`
8. `.codex/roadmap.md`
9. `.codex/next_task.md`

## Project constraints

- Do not redesign the architecture without explicit approval.
- Do not add unrelated features.
- Keep changes small and reviewable.
- Use Python 3.12.
- Use the `src` package layout.
- Use pytest for tests.
- Use type hints.
- Prefer composition over inheritance.
- Keep the design async-first where asynchronous behavior is relevant.
- Do not introduce global mutable state.
- Do not use `print()` in production code; use logging.
- Do not implement webhook, Git automation, AI generation, or pipeline functionality before the current stabilization work is complete.
- Preserve existing public APIs unless a change is explicitly approved.

## Token and context efficiency

- Prefer Serena semantic tools for source exploration: symbol overview, symbol lookup, references, then only the required symbol bodies.
- Do not read an entire large source file when a targeted symbol body is sufficient.
- Use repository-wide text search only when semantic tools cannot locate the target; expand the search scope gradually.
- Do not repeatedly read code that is already present in the current context.
- Exclude unrelated or generated paths unless they are required: `.git`, `.venv`, `__pycache__`, `.pytest_cache`, `build`, `dist`, `coverage`, and generated artifacts.
- For bugs, begin with the exact error, failing test, symbol, or call path.

## Model routing gate

- Before every new implementation or code-changing task, report the task, difficulty, recommended model, recommended reasoning level, and current setting.
- Do not infer the current model or reasoning level from stale conversation context. If the current setting is not confirmed, ask the user to confirm it before editing.
- If a model or reasoning change is recommended, stop before editing and wait until the user confirms the change.
- When the confirmed current setting is suitable and the user has said to proceed, continue without asking for duplicate approval.
- Follow `docs/development/model_routing.md` for the detailed routing policy and report format.

## Required workflow

Before editing:

1. Inspect the repository tree.
2. Read `pyproject.toml`.
3. Run `git status`.
4. Run `pytest`.
5. Explain the current failures.
6. Propose a minimal plan.
7. Wait for approval before broad refactoring.

After editing:

1. Run the relevant focused tests.
2. Run the full `pytest` suite.
3. Run `python -m autoforge.main version`.
4. Show changed files.
5. Summarize remaining issues.
6. Do not commit or push unless explicitly requested.
