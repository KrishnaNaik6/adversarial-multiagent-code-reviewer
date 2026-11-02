"""Configuration models and settings."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SandboxConfig(BaseSettings):
    """Configuration for Docker sandbox execution."""

    model_config = SettingsConfigDict(env_prefix="ADVERSARY_SANDBOX_")

    image: str = Field(default="python:3.12-slim", description="Docker image for test execution")
    network_disabled: bool = Field(default=True, description="Disable network inside container")
    memory_limit: str = Field(default="1g", description="Container RAM memory limit")
    cpu_period: int = Field(default=100000, description="CPU CFS scheduler period")
    cpu_quota: int = Field(default=100000, description="CPU CFS quota (100000 = 1 CPU)")
    pids_limit: int = Field(default=100, description="Maximum processes in container")
    timeout_seconds: int = Field(default=30, description="Execution timeout per test")
    run_as_non_root: bool = Field(
        default=True, description="Enforce non-root execution inside container"
    )


class AdversaryConfig(BaseSettings):
    """Main application configuration."""

    model_config = SettingsConfigDict(env_prefix="ADVERSARY_", env_file=".env", extra="ignore")

    workspace_dir: Path = Field(default_factory=Path.cwd, description="Target workspace directory")
    data_dir: Path = Field(
        default_factory=lambda: Path(".adversary"), description="Storage directory"
    )
    db_name: str = Field(default="adversary.db", description="SQLite database filename")
    log_level: str = Field(default="INFO", description="Logging verbosity")
    max_repair_attempts: int = Field(default=3, description="Maximum patch attempts per defect")
    ai_enabled: bool = Field(default=False, description="Enable optional AI assistance")
    ai_provider: str = Field(
        default="none", description="AI provider: none, openai, anthropic, gemini"
    )
    ai_api_key: str | None = Field(default=None, description="Optional API key for AI provider")
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)

    @property
    def db_path(self) -> Path:
        """Full path to SQLite database."""
        return self.data_dir / self.db_name

    @property
    def reports_dir(self) -> Path:
        """Directory for report output."""
        return self.data_dir / "reports"
