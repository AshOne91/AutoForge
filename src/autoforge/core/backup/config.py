from __future__ import annotations

from dataclasses import dataclass
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
