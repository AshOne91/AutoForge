from collections.abc import Mapping

from autoforge.core.secret import SecretReference, SecretValue


class InMemorySecretProvider:
    """테스트와 로컬 조립 전용 Secret Provider다."""

    def __init__(self, secrets: Mapping[str, str]) -> None:
        self._secrets = dict(secrets)

    async def resolve(self, reference: SecretReference) -> SecretValue:
        try:
            value = self._secrets[reference.name]
        except KeyError as error:
            raise KeyError(f"Secret reference was not found: {reference.name}") from error
        return SecretValue(value)
