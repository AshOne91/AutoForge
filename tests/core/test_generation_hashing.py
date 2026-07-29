from autoforge.core.generation import content_hash, specification_hash
from autoforge.core.specification import ApplicationSpec, ProjectInfo, ProjectSpec


def test_content_hash_is_deterministic_for_text_and_bytes() -> None:
    assert content_hash("AutoForge") == content_hash(b"AutoForge")
    assert content_hash("AutoForge") != content_hash("autoforge")


def test_specification_hash_ignores_mapping_key_order() -> None:
    first = {"project": {"name": "Game Server", "version": "0.1.0"}}
    second = {"project": {"version": "0.1.0", "name": "Game Server"}}

    assert specification_hash(first) == specification_hash(second)


def test_specification_hash_supports_pydantic_models() -> None:
    specification = ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="Game Server",
            package_name="game_server",
            version="0.1.0",
        ),
        application=ApplicationSpec(modules=["tutorial"]),
    )

    assert specification_hash(specification) == specification_hash(
        specification.model_dump(mode="json", by_alias=True)
    )
