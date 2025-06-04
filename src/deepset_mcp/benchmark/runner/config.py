import os
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BenchmarkConfig(BaseSettings):
    """Core configuration for the benchmark runner."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env vars
    )

    deepset_workspace: str = Field(default_factory=lambda: os.environ.get("DEEPSET_WORKSPACE", ""))
    deepset_api_key: str = Field(default_factory=lambda: os.environ.get("DEEPSET_API_KEY", ""))

    # Optional fields with defaults
    output_dir: Path = Field(default_factory=Path.cwd)
    test_case_base_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "tasks")

    # Store all other available env vars
    additional_env_vars: dict[str, str] = Field(default_factory=dict)

    @field_validator("deepset_workspace", "deepset_api_key")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Validate that the env var is not empty."""
        if not v or not v.strip():
            raise ValueError("DEEPSET_WORKSPACE or DEEPSET_API_KEY is empty.")
        return v

    def model_post_init(self, __context: Any) -> None:
        """After initialization, collect all available env vars."""
        # Collect all env vars that might be useful (excluding system ones)
        ignore_prefixes = ("PATH", "HOME", "USER", "SHELL", "TERM", "PWD", "LC_")

        for key, value in os.environ.items():
            # Skip system variables and already captured ones
            if (
                not any(key.startswith(prefix) for prefix in ignore_prefixes)
                and key not in ("DEEPSET_WORKSPACE", "DEEPSET_API_KEY")
                and value
            ):  # Only include non-empty values
                self.additional_env_vars[key] = value

    def check_required_env_vars(self, required_vars: list[str]) -> tuple[bool, list[str]]:
        """
        Check if all required environment variables are available.

        Returns:
            Tuple of (all_available, missing_vars)
        """
        available = self.get_all_env_vars()
        missing = [var for var in required_vars if var not in available]
        return len(missing) == 0, missing

    def get_env_var(self, key: str) -> str:
        """Get a specific environment variable."""
        all_vars = self.get_all_env_vars()
        return all_vars[key]

    def get_all_env_vars(self) -> dict[str, str]:
        """Get all available environment variables."""
        return {
            "DEEPSET_WORKSPACE": self.deepset_workspace,
            "DEEPSET_API_KEY": self.deepset_api_key,
            **self.additional_env_vars,
        }
