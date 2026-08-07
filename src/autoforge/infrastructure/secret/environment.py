import os
import re
from collections.abc import Mapping

from autoforge.core.secret import SecretReference, SecretValue

_ENVIRONMENT_NAME = re.compile(r"[A-Z_][A-Z0-9_]*")


class EnvironmentSecretNotFoundError(RuntimeError):
    pass


class EnvironmentSecretProvider:
    """Resolve declared secret references from explicitly mapped environment keys."""

    def __init__(
        self,
        *,
        secret_names: Mapping[str, str],
        environment: Mapping[str, str] | None = None,
    ) -> None:
        normalized: dict[str, str] = {}
        for reference_name, environment_name in secret_names.items():
            SecretReference(reference_name)
            if _ENVIRONMENT_NAME.fullmatch(environment_name) is None:
                raise ValueError("Environment secret variable name is invalid")
            normalized[reference_name] = environment_name
        self._secret_names = normalized
        self._environment = environment if environment is not None else os.environ

    async def resolve(self, reference: SecretReference) -> SecretValue:
        environment_name = self._secret_names.get(reference.name)
        if environment_name is None:
            raise EnvironmentSecretNotFoundError(
                "Environment secret reference is not configured"
            )
        value = self._environment.get(environment_name)
        if not value:
            raise EnvironmentSecretNotFoundError(
                "Environment secret value is not configured"
            )
        return SecretValue(value)
