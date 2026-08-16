from __future__ import annotations

from contextlib import AsyncExitStack
from importlib import import_module
from pathlib import Path
from typing import Any, Self
from urllib.parse import urlsplit

from autoforge.core.backup import S3StorageConfig
from autoforge.core.secret import SecretProvider


class Aioboto3S3Client:
    """Lifecycle-safe aioboto3 client implementing the backup client seam."""

    def __init__(
        self,
        configuration: S3StorageConfig,
        *,
        secret_provider: SecretProvider | None = None,
        region_name: str = "us-east-1",
    ) -> None:
        self._configuration = configuration
        self._secret_provider = secret_provider
        self._region_name = region_name
        self._stack: AsyncExitStack | None = None
        self._client: Any = None

    async def __aenter__(self) -> Self:
        module = self._load_module()
        if self._configuration.access_key_id and self._secret_provider is None:
            raise ValueError("secret_provider is required for configured credentials")

        client_kwargs: dict[str, str] = {
            "service_name": "s3",
            "region_name": self._region_name,
            "endpoint_url": self._configuration.endpoint,
        }
        if self._secret_provider is not None:
            access_key = await self._secret_provider.resolve(
                self._configuration.access_key_id
            )
            secret_key = await self._secret_provider.resolve(
                self._configuration.secret_access_key
            )
            client_kwargs.update(
                aws_access_key_id=access_key.reveal(),
                aws_secret_access_key=secret_key.reveal(),
            )

        session = module.Session()
        self._stack = AsyncExitStack()
        self._client = await self._stack.enter_async_context(
            session.client(**client_kwargs)
        )
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        if self._stack is not None:
            await self._stack.aclose()
        self._stack = None
        self._client = None

    async def put_file(
        self,
        *,
        bucket: str,
        key: str,
        source: Path,
        expected_sha256: str,
    ) -> str:
        client = self._require_client()
        with source.open("rb") as file_object:
            await client.upload_fileobj(
                file_object,
                bucket,
                key,
                ExtraArgs={"Metadata": {"sha256": expected_sha256}},
            )
        return f"s3://{bucket}/{key}"

    async def verify_object(self, object_id: str, *, expected_sha256: str) -> None:
        client = self._require_client()
        parsed = urlsplit(object_id)
        if parsed.scheme != "s3" or parsed.netloc != self._configuration.bucket:
            raise ValueError("object_id is not an S3 object in the configured bucket")
        response = await client.head_object(
            Bucket=parsed.netloc,
            Key=parsed.path.lstrip("/"),
        )
        actual = response.get("Metadata", {}).get("sha256", "").lower()
        if actual != expected_sha256.lower():
            raise ValueError("remote backup checksum does not match the manifest")

    @staticmethod
    def _load_module() -> Any:
        try:
            return import_module("aioboto3")
        except ImportError as exc:
            raise RuntimeError(
                "Install the optional 'backup' extra to use the aioboto3 client"
            ) from exc

    def _require_client(self) -> Any:
        if self._client is None:
            raise RuntimeError("Aioboto3S3Client must be used inside an async context")
        return self._client
