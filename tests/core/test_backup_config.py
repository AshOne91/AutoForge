import pytest

from autoforge.core.backup import S3StorageConfig
from autoforge.core.secret import SecretReference


def test_s3_storage_config_normalizes_prefix_without_storing_credentials() -> None:
    config = S3StorageConfig(
        endpoint="http://minio:9000",
        bucket="backups",
        prefix="/autoforge/",
        access_key_id=SecretReference("storage/access-key"),
        secret_access_key=SecretReference("storage/secret-key"),
    )

    assert config.prefix == "autoforge"
    assert config.access_key_id == SecretReference("storage/access-key")
    assert "minio:9000" in config.endpoint


@pytest.mark.parametrize(
    "kwargs",
    [
        {"endpoint": "minio:9000", "bucket": "backups"},
        {"endpoint": "http://minio:9000", "bucket": ""},
        {"endpoint": "http://minio:9000", "bucket": "back/up"},
        {
            "endpoint": "http://user:pass@minio:9000",
            "bucket": "backups",
        },
    ],
)
def test_s3_storage_config_rejects_invalid_target(kwargs: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        S3StorageConfig(**kwargs)


def test_s3_storage_config_requires_both_credential_references() -> None:
    with pytest.raises(ValueError):
        S3StorageConfig(
            endpoint="http://minio:9000",
            bucket="backups",
            access_key_id=SecretReference("storage/access-key"),
        )
