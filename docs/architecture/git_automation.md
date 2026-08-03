# Git Automation Architecture

- 확정일: 2026-08-03
- 현재 범위: repository submission과 Job별 격리 checkout 실행

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
향후 Secret Provider와 Git Provider Plugin이 파일·로그·process list에 노출하지 않는
방식으로 주입한다.

## 현재 구현과 남은 범위

현재 `SubprocessGitProvider`는 안전한 clone, commit 해석, detached checkout과 clean
working tree 검증을 구현한다. 원격 GenerationJob은 HTTP 제출 시 로컬 파일을 읽지 않고
미계획 pending 상태로 저장된다. worker가 Job별 Workspace에 checkout한 뒤에만 명세를
읽고, 생성 unit과 명세 hash 및 확정 commit SHA를 lease로 원자적으로 저장한다. 이후
동일 checkout 안에서 Generation/Validation Pipeline을 실행한다.

성공한 Workspace는 삭제하고, 설정에 따라 실패 Workspace는 분석용으로 보존할 수 있다.
Windows의 읽기 전용 Git object도 안전하게 정리한다. 실제 로컬 repository 통합
테스트에서 성공·실패 모두 원본 저장소가 변하지 않으며 확정된 commit에서만 생성되는
것을 검증했다.

남은 범위:

- 검증 성공 후 작업 branch 생성과 변경 allowlist
- author/signing 정책을 적용한 commit
- credential Secret Provider, push와 Pull Request adapter
- force push 금지, protected branch와 fork/PR 정책
