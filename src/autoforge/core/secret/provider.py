from typing import Protocol

from autoforge.core.secret.models import SecretReference, SecretValue


class SecretProvider(Protocol):
    async def resolve(self, reference: SecretReference) -> SecretValue: ...
