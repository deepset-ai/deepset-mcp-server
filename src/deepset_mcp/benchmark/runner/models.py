from pathlib import Path
from typing import Any, Self

import yaml
from pydantic import BaseModel, Field, PrivateAttr, ValidationError, model_validator


class TestCaseConfig(BaseModel):
    """
    Pydantic v2 model for a single “benchmark/tasks/<test>.yml” file.

    Provides a `from_file()` constructor that:
    - Reads the YAML from disk.
    - Resolves `query_yaml`, `index_yaml`, `expected_query` as paths relative to the YAML file’s directory.
    - Validates that at least one of query/index is present, that paired fields (query_name/index_name) exist,
      and that each referenced file actually exists on disk.
    """

    name: str = Field(
        ...,
        description="Unique identifier for this test case (snake_case, no spaces).",
        pattern=r"^[a-z0-9_]+$",
    )
    objective: str = Field(..., description="A short description of what this test is about.")
    prompt: str = Field(..., description="The prompt text to send to the Agent.")
    query_yaml: str | None = Field(None, description="Relative or absolute path to a query pipeline YAML.")
    query_name: str | None = Field(
        None, description="Name to assign to the ‘query’ pipeline if `query_yaml` is present."
    )
    index_yaml: str | None = Field(None, description="Relative or absolute path to an indexing pipeline YAML.")
    index_name: str | None = Field(None, description="Name to assign to the Index if `index_yaml` is present.")
    expected_query: str | None = Field(
        None, description="(Optional) Relative or absolute path to a 'gold' query pipeline YAML."
    )
    expected_index: str | None = Field(None, description="(Optional) Relative or absolute path to a 'gold' index YAML.")
    tags: list[str] = Field(default_factory=list, description="Tags (e.g. [api-outputs, debug]).")
    judge_prompt: str | None = Field(
        None,
        description="(Optional) Prompt to use for a judge LLM to verify correctness.",
    )

    # These PrivateAttrs will hold the raw YAML‐as‐text after reading from disk:
    _query_yaml_text: str | None = PrivateAttr(default=None)
    _index_yaml_text: str | None = PrivateAttr(default=None)
    _expected_query_text: str | None = PrivateAttr(default=None)
    _expected_index_text: str | None = PrivateAttr(default=None)

    @model_validator(mode="before")
    def _check_at_least_one(cls, values: dict[str, str]) -> dict[str, str]:
        """Before any field‐level validation, ensure at least one of `query_yaml` or `index_yaml` is provided."""
        if not values.get("query_yaml") and not values.get("index_yaml"):
            raise ValueError("At least one of `query_yaml` or `index_yaml` must be provided.")
        return values

    @model_validator(mode="after")
    def _load_yaml_files(self) -> Self:
        """
        Hook to load YAML contents from disk.

        After all standard field validation has passed, this hook:

        1) If `query_yaml` is set:
           - Ensures `query_name` is also set.
           - Reads the file from disk into `_query_yaml_text`.
        2) If `index_yaml` is set:
           - Ensures `index_name` is also set.
           - Reads the file from disk into `_index_yaml_text`.
        3) If `expected_query` is set:
           - Reads that file into `_expected_query_text`.
        Any missing paired field or missing file will raise an error.
        """
        # 1) Query pipeline YAML → text
        if self.query_yaml:
            if not self.query_name:
                raise ValueError("`query_name` must be provided if `query_yaml` is set.")
            path = Path(self.query_yaml)
            if not path.is_file():
                raise FileNotFoundError(f"query_yaml file not found: {self.query_yaml}")
            self._query_yaml_text = path.read_text(encoding="utf-8")

        # 2) Index YAML → text
        if self.index_yaml:
            if not self.index_name:
                raise ValueError("`index_name` must be provided if `index_yaml` is set.")
            path = Path(self.index_yaml)
            if not path.is_file():
                raise FileNotFoundError(f"index_yaml file not found: {self.index_yaml}")
            self._index_yaml_text = path.read_text(encoding="utf-8")

        # 3) Expected “gold” pipeline YAML → text
        if self.expected_query:
            path = Path(self.expected_query)
            if not path.is_file():
                raise FileNotFoundError(f"expected_query file not found: {self.expected_query}")
            self._expected_query_text = path.read_text(encoding="utf-8")

        if self.expected_index:
            path = Path(self.expected_index)
            if not path.is_file():
                raise FileNotFoundError(f"expected_index file not found: {self.expected_index}")
            self._expected_index_text = path.read_text(encoding="utf-8")

        return self

    def get_query_yaml_text(self) -> str | None:
        """Return the raw text of the query‐pipeline YAML (or None if not set)."""
        return self._query_yaml_text

    def get_index_yaml_text(self) -> str | None:
        """Return the raw text of the index YAML (or None if not set)."""
        return self._index_yaml_text

    def get_expected_query_text(self) -> str | None:
        """Return the raw text of the expected “gold” pipeline YAML (or None)."""
        return self._expected_query_text

    def get_expected_index_text(self) -> str | None:
        """Return the raw text of the expected 'gold' index YAML (or None)."""
        return self._expected_index_text

    @classmethod
    def from_file(cls, cfg_path: Path) -> Self:
        """
        Read a test-case YAML from `cfg_path`, then initialize and return a TestCaseConfig instance.

        Raises:
          - FileNotFoundError if cfg_path doesn’t exist.
          - ValidationError if any field is invalid or any referenced file is missing.
        """
        if not cfg_path.is_file():
            raise FileNotFoundError(f"Test-case config not found: {cfg_path}")

        raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValidationError(f"Invalid test-case YAML at {cfg_path}; expected a mapping.")

        base_dir = cfg_path.parent

        # For each of query_yaml, index_yaml, expected_query: if present and relative, make it absolute.
        for field_name in ("query_yaml", "index_yaml", "expected_query"):
            p = raw.get(field_name)
            if p:
                # Only rewrite if it’s not already absolute
                candidate = Path(p)
                if not candidate.is_absolute():
                    raw[field_name] = str((base_dir / candidate).resolve())

        return cls(**raw)


class AgentConfig(BaseModel):
    """Agent configuration with flexible loading patterns."""

    agent_json: str | None = Field(None, description="Relative or absolute path to an agent JSON file.")

    agent_factory_function: str | None = Field(None, description="Qualified name of Agent factory function.")

    display_name: str = Field(..., description="Display name for the agent.")

    interactive: bool = Field(False, description="Whether to run the agent in interactive mode.")

    required_env_vars: list[str] = Field(
        default_factory=list, description="Required environment variables to run the agent."
    )

    @model_validator(mode="before")
    @classmethod
    def check_mutually_exclusive(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Ensure exactly one loading method is specified."""
        methods = [values.get("agent_json"), values.get("agent_factory_function")]

        if sum(bool(m) for m in methods) != 1:
            raise ValueError("Exactly one of agent_json or agent_factory_function must be provided")
        return values

    @model_validator(mode="after")
    def validate_files_exist(self) -> Self:
        """Validate that referenced files exist."""
        if self.agent_json:
            json_path = Path(self.agent_json)
            if not json_path.is_file():
                raise FileNotFoundError(f"Agent JSON file not found: {self.agent_json}")
        return self

    @classmethod
    def from_file(cls, cfg_path: Path) -> Self:
        """Read agent config from YAML file."""
        if not cfg_path.is_file():
            raise FileNotFoundError(f"Agent config not found: {cfg_path}")

        raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"Invalid agent config YAML at {cfg_path}; expected a mapping.")

        base_dir = cfg_path.parent

        # Resolve relative paths for agent_json
        if "agent_json" in raw and raw["agent_json"]:
            json_path = Path(raw["agent_json"])
            if not json_path.is_absolute():
                raw["agent_json"] = str((base_dir / json_path).resolve())

        return cls(**raw)
