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


def test_s3_storage_config_reads_generated_environment_contract() -> None:
    config = S3StorageConfig.from_environment(
        {
            "S3_ENDPOINT_URL": "http://minio:9000",
            "S3_BUCKET": "backups",
            "S3_PREFIX": "backups",
            "S3_ACCESS_KEY": "autoforge",
            "S3_SECRET_KEY": "change-me",
        }
    )

    assert config.endpoint == "http://minio:9000"
    assert config.bucket == "backups"
    assert config.prefix == "backups"
    assert config.access_key_id == SecretReference("S3_ACCESS_KEY")
    assert config.secret_access_key == SecretReference("S3_SECRET_KEY")


def test_s3_storage_config_requires_generated_endpoint_and_bucket() -> None:
    with pytest.raises(ValueError, match="S3_BUCKET"):
        S3StorageConfig.from_environment({"S3_ENDPOINT_URL": "http://minio:9000"})


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
