# 생성 결과 검증 환경

AutoForge의 `generate` 명령은 생성 결과를 다음 순서로 검증합니다.

1. 생성 패키지 import
2. 생성 프로젝트 pytest
3. Ruff 검사
4. wheel 빌드

검증 대상 프로젝트의 의존성이 별도 가상환경에 설치되어 있다면
`--validation-python`으로 해당 Python 실행 파일을 지정합니다.

```powershell
python -m autoforge.main generate `
  --project autoforge.yaml `
  --specifications specifications `
  --output . `
  --validation-python .venv\Scripts\python.exe
```

검증 대상 환경에는 프로젝트 의존성과 빌드 백엔드가 필요합니다.

```powershell
python -m pip install -e ".[test]"
python -m pip install "setuptools>=68"
```

`--validation-python`을 생략하면 AutoForge를 실행한 Python을 사용합니다.
AutoForge는 검증을 위해 의존성을 자동 설치하지 않으며, 비밀값이나 외부
서비스 접속정보를 생성물에 기록하지 않습니다.
