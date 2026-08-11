# Git Automation Architecture

## 목적과 책임 경계

AutoForge는 사용자의 원본 working tree에서 직접 코드를 생성하지 않는다. Git Provider는
원격 repository와 revision을 Job별 격리 Workspace에 가져오는 infrastructure adapter다.
Generator는 Git을 모르고, Git Provider는 생성 규칙을 모른다.

```text
GenerationJob
  → IsolatedWorkspaceManager
  → GitProvider.checkout(request, workspace)
  → exact commit detached checkout
  → Generation/Validation Pipeline
  → 성공한 경우에만 후속 branch/commit
```

checkout 완료는 commit이나 push 권한을 의미하지 않는다. branch, commit, push와 pull
request는 각각 별도 계약과 검증 gate를 통과해야 한다.

`GitCommitRequest`는 예상 base commit SHA, 작업 branch, 한 줄 commit message,
author identity, 선택적 signing fingerprint와 변경 허용 경로를 가진다. adapter는 현재
HEAD가 예상 SHA와 같은지 확인하고 실제 변경 전체가 허용 경로의 부분집합인지 확인한
뒤에만 branch를 만들고 stage한다. stage 결과도 검증된 변경 집합과 정확히 같아야 한다.

## Core 계약

`GitCheckoutRequest`는 repository URL, revision과 Workspace 상대 destination만 가진다.
`GitProvider` Protocol은 특정 Git library나 GitHub API를 Core에 노출하지 않는다.
`GitCheckoutResult`는 해석된 commit SHA, checkout 경로와 비밀정보가 없는 remote URL을
반환한다.

## Repository 정책

운영 remote는 다음 조건을 만족해야 한다.

- scheme은 `https` 또는 canonical `ssh://`
- host는 주입된 allowlist에 존재
- HTTPS URL에 username/password/token 금지
- SSH user는 없거나 `git`
- query, fragment와 `..` path 금지
- SCP 축약형보다 파싱 가능한 canonical URL 사용

로컬 경로는 기본적으로 금지한다. 테스트와 명시적 내부 사용에서만
`allowed_local_roots` 내부의 실제 디렉터리를 허용한다. Windows drive와 UNC 경로는 URL
scheme으로 오인하지 않고 local policy로 검증한다.

revision은 option처럼 시작하거나 공백, control character, Git ref 특수문자, `..`,
`@{`를 포함할 수 없다. clone 후 `rev-parse --verify <revision>^{commit}`으로 commit
object를 확정하고 그 SHA를 detached checkout한다. 따라서 branch가 checkout 도중
이동해도 이후 단계는 확정된 SHA를 사용한다.

## Process와 credential 경계

Git 명령은 shell 없이 argument tuple로 실행한다. 다음 환경을 명시적으로 주입한다.

```text
GIT_CONFIG_NOSYSTEM=1
GIT_CONFIG_GLOBAL=<null device>
GIT_TERMINAL_PROMPT=0
GCM_INTERACTIVE=Never
```

host의 system/global Git config와 대화형 credential prompt가 worker 동작을 바꾸는 것을
막는다. token을 URL이나 command argument에 넣지 않는다. private repository credential은
`SecretReference`만 Job에 저장하고 실행 직전에 `SecretProvider`로 resolve한다. HTTPS
credential은 secret을 포함하지 않는 일회용 askpass helper와 process environment로만
전달한다. helper 파일에는 username과 password를 기록하지 않으며 Git 명령 직후 즉시
삭제한다. 실제 secret 값은 URL과 command tuple에 포함하지 않는다.

## Worker delivery lifecycle

`SubprocessGitProvider`는 안전한 clone, commit 해석, detached checkout, clean
working tree 검증과 검증된 commit/push를 제공한다. 원격 GenerationJob은 HTTP
제출 시 로컬 파일을 읽지 않고 pending 상태로 저장된다. Worker가 Job별
Workspace에 checkout한 뒤 명세 Hash와 확정 Commit SHA를 저장하고 같은 checkout에서
Generation/Validation Pipeline을 실행한다.

성공한 Workspace는 삭제하고, 설정에 따라 실패 Workspace는 분석용으로 보존할 수 있다.
Windows의 읽기 전용 Git object도 안전하게 정리한다. 실제 로컬 repository 통합
테스트에서 성공·실패 모두 원본 저장소가 변하지 않으며 확정된 commit에서만 생성되는
것을 검증했다.

`SubprocessGitProvider.commit_validated()`는 검증된 변경만 작업 branch에 commit한다.
예상 base SHA 불일치, 허용 목록 밖 변경, rename/copy, 위험한 branch·message·identity와
중복 경로를 branch 생성 전에 거부한다. 변경이 없으면 branch나 빈 commit을 만들지
않는다. Git system/global config와 대화형 credential 차단은 checkout과 동일하게
적용한다. unsigned commit은 명시적인 `--no-gpg-sign`, signed commit은 요청의 16진수
fingerprint를 사용한다.

Git commit 설정이 주입된 Worker는 검증 후 Job을 `committing`으로 저장하고,
manifest의 created/changed 파일과 `.autoforge/manifest.json`만 allowlist로 계산한다.
Commit 성공 후 Push 설정이 있으면 `pushing`, Pull Request 설정까지 있으면
`opening_pull_request`를 거쳐 `succeeded`로 전이한다. 각 단계의 결과는 다음
단계를 실행하기 전에 JobStore에 저장하며 실패는 `failed`로 저장한다. 설정되지
않은 Delivery 단계는 건너뛴다.

`push_validated()`는 현재 HEAD와 branch가 요청의 commit SHA·작업 branch와 정확히
일치하는지 확인한다. policy의 작업 branch prefix만 허용하고 `main`, `master` 같은 보호
branch는 명령 실행 전에 거부한다. push 명령에는 force 계열 option을 제공하지 않는다.
remote가 이미 같은 SHA이면 성공한 멱등 재호출로 처리하고, remote가 다른 이력으로
진행된 non-fast-forward push는 Git의 안전 거부를 그대로 실패로 전파한다.

Worker는 `GitCommit*Event`, `GitPush*Event`, `PullRequest*Event`를 단계별로
발행한다. Push와 Pull Request는 저장된 Commit SHA를 기준으로 fencing한다.

## Pull Request contract boundary

Pull Request creation belongs to a hosting-service API, not to the local Git
process adapter. `GitProvider` therefore remains responsible only for checkout,
validated commit, and validated push. The independent `PullRequestProvider`
contract creates or returns the existing matching Pull Request.

`GitPullRequestRequest` carries the repository URL, expected remote head SHA, head
and base branches, title, body, and a secret reference. It never carries the token
value. `GitPullRequestPolicy` permits only configured generated-branch prefixes as
heads and configured protected branches as bases. The head and base must differ.

`create_or_get()` intentionally defines idempotent behavior. A hosting adapter must
verify that the remote head branch still points to `expected_head_sha`, return an
existing open Pull Request for the same head/base pair when present, and create a
new one only when none exists.

## GitHub Pull Request adapter boundary

`GitHubPullRequestProvider` implements the hosting-service contract through an
injected async `GitHubApiClient`. The adapter validates the generated head and
protected base policy before resolving credentials, verifies the remote head ref
against the expected commit SHA, searches for an existing open head/base Pull
Request, and creates one only when none exists.

The adapter treats a create-time HTTP 422 as a possible concurrent creation and
queries once more. It succeeds only when that query returns the exact requested
head branch, base branch, and head SHA. All other malformed, ambiguous, stale, or
unexpected responses fail closed. The API token is resolved immediately before
the calls and appears only in the authorization header supplied to the transport.

## GitHub HTTP transport boundary

`HttpxGitHubApiClient` is the production async transport for the injected GitHub
API contract. It uses a shared `httpx.AsyncClient` with TLS verification enabled,
an explicit timeout, environment proxy and `.netrc` discovery disabled, and HTTP
redirect following disabled. It accepts only relative `/repos/` GET and POST paths,
so a caller cannot redirect an authorization header to an arbitrary origin.

Responses are streamed into a bounded buffer before JSON decoding. Timeout and
transport exceptions are replaced with fixed messages that do not include request
headers, token values, URLs, or response bodies. The client exposes `aclose()` and
an async context manager so the Application composition root can own connection
pool shutdown explicitly.
## GenerationJob Pull Request lifecycle

When Pull Request settings and a provider are configured, a successful push moves
the Job to `opening_pull_request` instead of directly to `succeeded`. The worker
calls the idempotent provider with the persisted push SHA and branch, then stores
the exact `GitPullRequestResult` before completing the Job. Failure is persisted
before `PullRequestFailedEvent` is published.

Workers without Pull Request settings use the push-to-success path.
Pull Request execution requires commit and push settings, so it cannot bypass the
validated commit or remote SHA fencing stages.

## Environment secret adapter

`EnvironmentSecretProvider` is a deployment-oriented adapter for the existing
`SecretProvider` contract. It accepts an explicit mapping from a stored secret
reference name to an environment-variable name, then resolves the value only when
the Git or GitHub adapter needs it. The mapping prevents lossy automatic name
conversion and keeps secret values out of YAML, Job documents, URLs, and command
arguments.

It is intentionally not a global configuration reader. The application composition
root receives the mapping from deployment configuration and injects this provider
into both Git checkout/push and Pull Request adapters.

## Configuration model boundary

`Settings.git_automation` is optional and disabled by default, so existing
`autoforge.yaml` files keep their behavior. When enabled, it requires at least one
explicit secret-reference mapping and validates timeout, remote, and Pull Request
metadata limits. The mapping contains environment variable names only; it never
contains resolved secret values.

This model is configuration data, not a composition root. It does not instantiate
HTTP clients, workers, database stores, or secret providers. The deployment
entrypoint assembles those dependencies explicitly.

## Git automation composition root

`autoforge.composition`은 새로운 업무 계층이 아니라 배포 진입점이 소유하는 최외곽
조립 경계다. `create_git_automation_components()`는 Git 자동화가 활성화된 경우에만
다음 객체를 명시적으로 생성한다.

- 환경 변수 이름만 가진 설정에서 `EnvironmentSecretProvider` 생성
- 동일한 repository host, 작업 branch prefix와 보호 branch 정책을 Git push와 PR에 적용
- `SubprocessGitProvider`, `HttpxGitHubApiClient`, `GitHubPullRequestProvider` 조립
- worker에 주입할 commit, push와 Pull Request 설정 생성

HTTP 연결 풀은 `GitAutomationComponents.aclose()`로 composition root가 직접 종료한다.
비활성 설정은 `None`을 반환하므로 기존 로컬 CLI와 생성 흐름에는 Git 권한이나 네트워크
클라이언트가 추가되지 않는다. 배포 진입점은 이 객체를 JobStore, Pipeline,
Workspace와 함께 Worker에 주입한다.
