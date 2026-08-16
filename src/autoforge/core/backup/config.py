from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Self
from urllib.parse import urlsplit

from autoforge.core.secret import SecretReference


@dataclass(frozen=True, slots=True)
class S3StorageConfig:
    """Provider-neutral settings for an S3-compatible backup target."""

    endpoint: str
    bucket: str
    prefix: str = ""
    access_key_id: SecretReference | None = None
    secret_access_key: SecretReference | None = None

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str],
        *,
        endpoint_variable: str = "S3_ENDPOINT_URL",
        bucket_variable: str = "S3_BUCKET",
        prefix_variable: str = "S3_PREFIX",
        access_key_variable: str = "S3_ACCESS_KEY",
        secret_key_variable: str = "S3_SECRET_KEY",
    ) -> Self:
        """Build a config from generated environment names without reading secrets."""

        def required(variable: str) -> str:
            value = environment.get(variable)
            if not value:
                raise ValueError(f"S3 environment variable is not configured: {variable}")
            return value

        return cls(
            endpoint=required(endpoint_variable),
            bucket=required(bucket_variable),
            prefix=environment.get(prefix_variable, ""),
            access_key_id=SecretReference(access_key_variable),
            secret_access_key=SecretReference(secret_key_variable),
        )

    def __post_init__(self) -> None:
        parsed = urlsplit(self.endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("S3 endpoint must be an absolute HTTP(S) URL")
        if parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise ValueError("S3 endpoint must not contain credentials or query data")
        if not self.bucket or self.bucket != self.bucket.strip() or "/" in self.bucket:
            raise ValueError("S3 bucket must be a non-empty name")
        if any(ord(character) < 32 for character in self.prefix):
            raise ValueError("S3 prefix must not contain control characters")
        object.__setattr__(self, "prefix", self.prefix.strip("/"))
        if (self.access_key_id is None) != (self.secret_access_key is None):
            raise ValueError("S3 credential references must be provided together")
