from pathlib import Path

from croc.storage.model_registry import ModelRegistry


def create_artifact(path: Path, name: str) -> Path:
    artifact = path / name
    artifact.write_text(name)
    return artifact


def test_registry_activate_and_rollback(tmp_path):
    registry = ModelRegistry(tmp_path)
    artifact_a = create_artifact(tmp_path, "model_a.zip")
    version_a = registry.register_version(
        artifact_a,
        code_sha="sha-a",
        metrics={"sharpe": 1.0},
        config={"algo": "ppo"},
    )
    registry.activate(version_a.version)
    active = registry.active_model()
    assert active is not None
    assert active.read_text() == "model_a.zip"

    artifact_b = create_artifact(tmp_path, "model_b.zip")
    version_b = registry.register_version(
        artifact_b,
        code_sha="sha-b",
        metrics={"sharpe": 1.2},
        config={"algo": "ppo"},
    )
    registry.activate(version_b.version)
    assert registry.active_model().read_text() == "model_b.zip"

    registry.rollback(version_a.version)
    assert registry.active_model().read_text() == "model_a.zip"
