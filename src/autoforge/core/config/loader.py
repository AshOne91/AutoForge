from pathlib import Path

import yaml

from autoforge.core.config.settings import Settings


class ConfigLoader:
    """autoforge.yaml 파일을 읽어 Settings 객체를 생성한다."""

    @staticmethod
    def load(path: str = "autoforge.yaml") -> Settings:
        config_path = Path(path)

        if not config_path.exists():
            raise FileNotFoundError(
                f"설정 파일을 찾을 수 없습니다: {config_path}"
            )

        with config_path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

        return Settings(**data)