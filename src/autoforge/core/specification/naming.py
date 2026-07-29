import keyword
import re

PYTHON_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
CLASS_NAME_PATTERN = re.compile(r"^[A-Z][A-Za-z0-9]*$")
SEMANTIC_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")

WINDOWS_RESERVED_NAMES = {
    "aux",
    "clock$",
    "con",
    "nul",
    "prn",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}


def validate_python_name(value: str) -> str:
    if not PYTHON_NAME_PATTERN.fullmatch(value):
        raise ValueError(
            "이름은 소문자로 시작하고 소문자, 숫자, 밑줄만 포함해야 합니다."
        )
    if keyword.iskeyword(value):
        raise ValueError("Python 예약어는 이름으로 사용할 수 없습니다.")
    if value.startswith("__") or value.endswith("__"):
        raise ValueError("이중 밑줄로 시작하거나 끝나는 이름은 사용할 수 없습니다.")
    if value.casefold() in WINDOWS_RESERVED_NAMES:
        raise ValueError("운영체제 예약 이름은 사용할 수 없습니다.")
    return value


def validate_class_name(value: str) -> str:
    if not CLASS_NAME_PATTERN.fullmatch(value):
        raise ValueError(
            "클래스 이름은 대문자로 시작하고 영문자와 숫자만 포함해야 합니다."
        )
    return value


def validate_semantic_version(value: str) -> str:
    if not SEMANTIC_VERSION_PATTERN.fullmatch(value):
        raise ValueError("버전은 '주버전.부버전.수정버전' 형식이어야 합니다.")
    return value


def validate_http_path(value: str) -> str:
    if not value.startswith("/"):
        raise ValueError("HTTP 경로는 '/'로 시작해야 합니다.")
    if "\\" in value:
        raise ValueError("HTTP 경로에는 역슬래시를 사용할 수 없습니다.")
    if ".." in value.split("/"):
        raise ValueError("HTTP 경로에는 '..' 구간을 사용할 수 없습니다.")
    if value != "/" and "//" in value:
        raise ValueError("HTTP 경로에는 빈 구간을 사용할 수 없습니다.")
    return value
