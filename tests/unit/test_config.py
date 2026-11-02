"""Unit tests for configuration management."""

from pathlib import Path

from adversary.config.settings import AdversaryConfig, SandboxConfig


def test_default_config() -> None:
    config = AdversaryConfig()
    assert config.db_name == "adversary.db"
    assert config.log_level == "INFO"
    assert config.max_repair_attempts == 3
    assert config.ai_enabled is False
    assert config.ai_provider == "none"
    assert config.sandbox.image == "python:3.12-slim"
    assert config.sandbox.network_disabled is True
    assert config.sandbox.run_as_non_root is True
    assert config.db_path == Path(".adversary") / "adversary.db"
    assert config.reports_dir == Path(".adversary") / "reports"


def test_custom_config(tmp_path: Path) -> None:
    sandbox = SandboxConfig(image="custom-image:1.0", timeout_seconds=60)
    config = AdversaryConfig(workspace_dir=tmp_path, max_repair_attempts=5, sandbox=sandbox)
    assert config.workspace_dir == tmp_path
    assert config.max_repair_attempts == 5
    assert config.sandbox.image == "custom-image:1.0"
    assert config.sandbox.timeout_seconds == 60
