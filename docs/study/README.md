# AutoForge 완전 입문 학습 시리즈

이 시리즈는 Python과 웹 개발을 처음 배우거나 오랜만에 다시 시작하는 사람을
위한 문서다. AutoForge 용어를 먼저 외우지 않는다. 작은 웹서버를 직접
이해한 뒤, 반복 작업을 왜 자동화하는지 순서대로 배운다.

## 권장 순서

1. [1권: Python과 웹 기초](01_PYTHON_AND_WEB_BASICS.md)
2. [2권: FastAPI 서버를 손으로 만들기](02_FASTAPI_FIRST_SERVER.md)
3. [3권: AutoForge 아키텍처 이해하기](03_AUTOFORGE_ARCHITECTURE.md)
4. [4권: AutoForge 실제 코드 읽기](04_READING_AUTOFORGE_CODE.md)
5. [2026-07-30 상세 학습 Snapshot](../AUTOFORGE_STUDY_GUIDE_2026-07-30.md)

이 시리즈는 이해를 돕는 STUDY 문서다. 정확한 현재 계약은
[`system_design.md`](../architecture/system_design.md)와 연결된 Canonical
Architecture가 소유하고, 구현 상태는
[`.codex/current_status.md`](../../.codex/current_status.md)가 소유한다.

한 번에 모두 읽을 필요는 없다. 각 권의 “이번 권에서 기억할 것”을 이해하면
다음 권으로 넘어간다.

## 공부 방법

- 코드를 눈으로만 읽지 말고 직접 입력한다.
- 한 줄씩 실행하고 결과를 확인한다.
- 모르는 단어가 나오면 그 단어가 설명된 바로 앞 절로 돌아간다.
- 처음에는 암기보다 데이터가 어디에서 어디로 가는지 본다.
- 테스트 실패는 고장이 아니라 예상과 실제가 다른 이유를 알려 주는 자료다.

## 전체 그림

```text
Python 문법
  ↓
HTTP 요청과 응답
  ↓
FastAPI로 작은 서버 작성
  ↓
서버를 반복해서 만들 때 생기는 문제
  ↓
AutoForge로 구조 생성과 검증 자동화
```

## 용어를 아주 짧게 미리 보기

| 용어 | 쉬운 뜻 |
|---|---|
| Python | 사람이 작성한 명령을 컴퓨터가 실행할 수 있게 하는 프로그래밍 언어 |
| 웹서버 | 요청을 받고 응답을 돌려주는 실행 중인 프로그램 |
| HTTP | 웹에서 요청과 응답을 주고받는 규칙 |
| API | 다른 프로그램이 사용할 수 있도록 공개한 기능의 입구 |
| FastAPI | Python으로 API 웹서버를 만들기 쉽게 해 주는 도구 |
| Uvicorn | FastAPI 애플리케이션을 실제로 실행하는 서버 |
| Pydantic | 입력 데이터의 형태와 값을 검사하는 도구 |
| pytest | 코드가 예상대로 동작하는지 자동으로 확인하는 도구 |
| AutoForge | 반복되는 FastAPI 프로젝트 구조를 만들고 검증하는 도구 |
