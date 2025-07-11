"""Unit tests for the benchmark configuration models."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from pydantic import ValidationError

from deepset_mcp.benchmark.core.config import AgentConfig, BenchmarkConfig, TestCaseConfig


class TestBenchmarkConfig:
    """Test suite for BenchmarkConfig class."""

    def test_init_with_valid_env_vars(self) -> None:
        """Test initialization with valid environment variables."""
        with patch.dict(os.environ, {"DEEPSET_WORKSPACE": "test_workspace", "DEEPSET_API_KEY": "test_key"}):
            config = BenchmarkConfig()
            assert config.deepset_workspace == "test_workspace"
            assert config.deepset_api_key == "test_key"

    def test_init_with_empty_env_vars(self) -> None:
        """Test initialization with empty environment variables raises validation error."""
        with patch.dict(os.environ, {"DEEPSET_WORKSPACE": "", "DEEPSET_API_KEY": "test_key"}):
            with pytest.raises(ValidationError) as exc_info:
                BenchmarkConfig()
            assert "DEEPSET_WORKSPACE or DEEPSET_API_KEY is empty" in str(exc_info.value)

    def test_init_with_missing_env_vars(self) -> None:
        """Test initialization with missing environment variables raises validation error."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                BenchmarkConfig()
            assert "DEEPSET_WORKSPACE or DEEPSET_API_KEY is empty" in str(exc_info.value)

    def test_default_values(self) -> None:
        """Test that default values are set correctly."""
        with patch.dict(os.environ, {"DEEPSET_WORKSPACE": "test_workspace", "DEEPSET_API_KEY": "test_key"}):
            config = BenchmarkConfig()
            assert config.output_dir == Path.cwd()
            # The test_case_base_dir is relative to the config.py file, not the test file
            expected_path = (
                Path(__file__).parent.parent.parent.parent.parent / "src" / "deepset_mcp" / "benchmark" / "tasks"
            )
            assert config.test_case_base_dir == expected_path

    def test_model_post_init_collects_env_vars(self) -> None:
        """Test that model_post_init collects additional environment variables."""
        test_env = {
            "DEEPSET_WORKSPACE": "test_workspace",
            "DEEPSET_API_KEY": "test_key",
            "CUSTOM_VAR": "custom_value",
            "ANOTHER_VAR": "another_value",
            "PATH": "/usr/bin",  # Should be ignored
            "HOME": "/home/user",  # Should be ignored
        }

        with patch.dict(os.environ, test_env, clear=True):
            config = BenchmarkConfig()

            assert "CUSTOM_VAR" in config.additional_env_vars
            assert config.additional_env_vars["CUSTOM_VAR"] == "custom_value"
            assert "ANOTHER_VAR" in config.additional_env_vars
            assert config.additional_env_vars["ANOTHER_VAR"] == "another_value"
            assert "PATH" not in config.additional_env_vars
            assert "HOME" not in config.additional_env_vars

    def test_check_required_env_vars_all_available(self) -> None:
        """Test check_required_env_vars when all variables are available."""
        with patch.dict(
            os.environ, {"DEEPSET_WORKSPACE": "test_workspace", "DEEPSET_API_KEY": "test_key", "CUSTOM_VAR": "value"}
        ):
            config = BenchmarkConfig()
            all_available, missing = config.check_required_env_vars(["DEEPSET_WORKSPACE", "CUSTOM_VAR"])
            assert all_available is True
            assert missing == []

    def test_check_required_env_vars_some_missing(self) -> None:
        """Test check_required_env_vars when some variables are missing."""
        with patch.dict(os.environ, {"DEEPSET_WORKSPACE": "test_workspace", "DEEPSET_API_KEY": "test_key"}):
            config = BenchmarkConfig()
            all_available, missing = config.check_required_env_vars(["DEEPSET_WORKSPACE", "MISSING_VAR"])
            assert all_available is False
            assert "MISSING_VAR" in missing

    def test_get_env_var(self) -> None:
        """Test get_env_var method."""
        with patch.dict(os.environ, {"DEEPSET_WORKSPACE": "test_workspace", "DEEPSET_API_KEY": "test_key"}):
            config = BenchmarkConfig()
            assert config.get_env_var("DEEPSET_WORKSPACE") == "test_workspace"
            assert config.get_env_var("DEEPSET_API_KEY") == "test_key"

    def test_get_all_env_vars(self) -> None:
        """Test get_all_env_vars method."""
        with patch.dict(
            os.environ, {"DEEPSET_WORKSPACE": "test_workspace", "DEEPSET_API_KEY": "test_key", "CUSTOM_VAR": "value"}
        ):
            config = BenchmarkConfig()
            all_vars = config.get_all_env_vars()
            assert all_vars["DEEPSET_WORKSPACE"] == "test_workspace"
            assert all_vars["DEEPSET_API_KEY"] == "test_key"
            assert all_vars["CUSTOM_VAR"] == "value"


class TestTestCaseConfig:
    """Test suite for TestCaseConfig class."""

    def test_init_with_valid_data(self) -> None:
        """Test initialization with valid data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            query_file = temp_path / "query.yaml"
            query_file.write_text("test query yaml content")

            config = TestCaseConfig(
                name="test_case",
                objective="Test objective",
                prompt="Test prompt",
                query_yaml=str(query_file),
                query_name="test_query",
                index_yaml=None,
                index_name=None,
                expected_query=None,
                expected_index=None,
                tags=["test", "debug"],
                judge_prompt=None,
            )

            assert config.name == "test_case"
            assert config.objective == "Test objective"
            assert config.prompt == "Test prompt"
            assert config.query_yaml == str(query_file)
            assert config.query_name == "test_query"
            assert config.tags == ["test", "debug"]

    def test_init_missing_both_yaml_files(self) -> None:
        """Test initialization fails when both query_yaml and index_yaml are missing."""
        with pytest.raises(ValidationError) as exc_info:
            TestCaseConfig(
                name="test_case",
                objective="Test objective",
                prompt="Test prompt",
                query_yaml=None,
                query_name=None,
                index_yaml=None,
                index_name=None,
                expected_query=None,
                expected_index=None,
                judge_prompt=None,
            )
        assert "At least one of `query_yaml` or `index_yaml` must be provided" in str(exc_info.value)

    def test_init_invalid_name_pattern(self) -> None:
        """Test initialization fails with invalid name pattern."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            query_file = temp_path / "query.yaml"
            query_file.write_text("test content")

            with pytest.raises(ValidationError) as exc_info:
                TestCaseConfig(
                    name="invalid-name-with-dashes",
                    objective="Test objective",
                    prompt="Test prompt",
                    query_yaml=str(query_file),
                    query_name="test_query",
                    index_yaml=None,
                    index_name=None,
                    expected_query=None,
                    expected_index=None,
                    judge_prompt=None,
                )
            assert "String should match pattern" in str(exc_info.value)

    def test_init_query_yaml_without_query_name(self) -> None:
        """Test initialization fails when query_yaml is provided without query_name."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            query_file = temp_path / "query.yaml"
            query_file.write_text("test content")

            with pytest.raises(ValidationError) as exc_info:
                TestCaseConfig(
                    name="test_case",
                    objective="Test objective",
                    prompt="Test prompt",
                    query_yaml=str(query_file),
                    query_name=None,
                    index_yaml=None,
                    index_name=None,
                    expected_query=None,
                    expected_index=None,
                    judge_prompt=None,
                )
            assert "`query_name` must be provided if `query_yaml` is set" in str(exc_info.value)

    def test_init_index_yaml_without_index_name(self) -> None:
        """Test initialization fails when index_yaml is provided without index_name."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            index_file = temp_path / "index.yaml"
            index_file.write_text("test content")

            with pytest.raises(ValidationError) as exc_info:
                TestCaseConfig(
                    name="test_case",
                    objective="Test objective",
                    prompt="Test prompt",
                    query_yaml=None,
                    query_name=None,
                    index_yaml=str(index_file),
                    index_name=None,
                    expected_query=None,
                    expected_index=None,
                    judge_prompt=None,
                )
            assert "`index_name` must be provided if `index_yaml` is set" in str(exc_info.value)

    def test_init_nonexistent_yaml_file(self) -> None:
        """Test initialization fails when referenced YAML file doesn't exist."""
        with pytest.raises(FileNotFoundError) as exc_info:
            TestCaseConfig(
                name="test_case",
                objective="Test objective",
                prompt="Test prompt",
                query_yaml="/nonexistent/file.yaml",
                query_name="test_query",
                index_yaml=None,
                index_name=None,
                expected_query=None,
                expected_index=None,
                judge_prompt=None,
            )
        assert "query_yaml file not found" in str(exc_info.value)

    def test_get_yaml_text_methods(self) -> None:
        """Test YAML text getter methods."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            query_file = temp_path / "query.yaml"
            query_content = "query: test content"
            query_file.write_text(query_content)

            expected_file = temp_path / "expected.yaml"
            expected_content = "expected: test content"
            expected_file.write_text(expected_content)

            config = TestCaseConfig(
                name="test_case",
                objective="Test objective",
                prompt="Test prompt",
                query_yaml=str(query_file),
                query_name="test_query",
                index_yaml=None,
                index_name=None,
                expected_query=str(expected_file),
                expected_index=None,
                judge_prompt=None,
            )

            assert config.get_query_yaml_text() == query_content
            assert config.get_expected_query_text() == expected_content
            assert config.get_index_yaml_text() is None
            assert config.get_expected_index_text() is None

    def test_from_file_valid_yaml(self) -> None:
        """Test from_file method with valid YAML file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create referenced files
            query_file = temp_path / "query.yaml"
            query_file.write_text("test query content")

            # Create config file
            config_data = {
                "name": "test_case",
                "objective": "Test objective",
                "prompt": "Test prompt",
                "query_yaml": "query.yaml",  # Relative path
                "query_name": "test_query",
                "tags": ["test"],
            }

            config_file = temp_path / "config.yaml"
            config_file.write_text(yaml.dump(config_data))

            config = TestCaseConfig.from_file(config_file)

            assert config.name == "test_case"
            assert config.objective == "Test objective"
            assert config.query_yaml == str(query_file.resolve())  # Should be absolute path now

    def test_from_file_nonexistent_file(self) -> None:
        """Test from_file method with nonexistent file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            TestCaseConfig.from_file(Path("/nonexistent/config.yaml"))
        assert "Test-case config not found" in str(exc_info.value)

    def test_from_file_invalid_yaml_content(self) -> None:
        """Test from_file method with invalid YAML content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            config_file = temp_path / "config.yaml"
            config_file.write_text("invalid: yaml: content: [")

            with pytest.raises(yaml.YAMLError):
                TestCaseConfig.from_file(config_file)

    def test_from_file_non_dict_yaml(self) -> None:
        """Test from_file method with non-dict YAML content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            config_file = temp_path / "config.yaml"
            config_file.write_text("- list\n- content")

            with pytest.raises(TypeError) as exc_info:
                TestCaseConfig.from_file(config_file)
            assert "ValidationError.__new__() missing 1 required positional argument" in str(exc_info.value)


class TestAgentConfig:
    """Test suite for AgentConfig class."""

    def test_init_with_agent_json(self) -> None:
        """Test initialization with agent_json."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            agent_file = temp_path / "agent.json"
            agent_file.write_text('{"agent": "config"}')

            config = AgentConfig(
                agent_json=str(agent_file),
                agent_factory_function=None,
                display_name="Test Agent",
                interactive=True,
                required_env_vars=["VAR1", "VAR2"],
            )

            assert config.agent_json == str(agent_file)
            assert config.display_name == "Test Agent"
            assert config.interactive is True
            assert config.required_env_vars == ["VAR1", "VAR2"]

    def test_init_with_agent_factory_function(self) -> None:
        """Test initialization with agent_factory_function."""
        config = AgentConfig(
            agent_json=None,
            agent_factory_function="module.create_agent",
            display_name="Test Agent",
            interactive=False,
        )

        assert config.agent_factory_function == "module.create_agent"
        assert config.display_name == "Test Agent"
        assert config.interactive is False
        assert config.required_env_vars == []

    def test_init_with_both_methods(self) -> None:
        """Test initialization fails when both methods are provided."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            agent_file = temp_path / "agent.json"
            agent_file.write_text('{"agent": "config"}')

            with pytest.raises(ValidationError) as exc_info:
                AgentConfig(
                    agent_json=str(agent_file),
                    agent_factory_function="module.create_agent",
                    display_name="Test Agent",
                    interactive=False,
                )
            assert "Exactly one of agent_json or agent_factory_function must be provided" in str(exc_info.value)

    def test_init_with_no_methods(self) -> None:
        """Test initialization fails when no methods are provided."""
        with pytest.raises(ValidationError) as exc_info:
            AgentConfig(
                agent_json=None,
                agent_factory_function=None,
                display_name="Test Agent",
                interactive=False,
            )
        assert "Exactly one of agent_json or agent_factory_function must be provided" in str(exc_info.value)

    def test_init_with_nonexistent_agent_json(self) -> None:
        """Test initialization fails when agent_json file doesn't exist."""
        with pytest.raises(FileNotFoundError) as exc_info:
            AgentConfig(
                agent_json="/nonexistent/agent.json",
                agent_factory_function=None,
                display_name="Test Agent",
                interactive=False,
            )
        assert "Agent JSON file not found" in str(exc_info.value)

    def test_from_file_valid_yaml(self) -> None:
        """Test from_file method with valid YAML file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create referenced agent file
            agent_file = temp_path / "agent.json"
            agent_file.write_text('{"agent": "config"}')

            # Create config file
            config_data = {
                "agent_json": "agent.json",  # Relative path
                "display_name": "Test Agent",
                "interactive": True,
                "required_env_vars": ["VAR1", "VAR2"],
            }

            config_file = temp_path / "config.yaml"
            config_file.write_text(yaml.dump(config_data))

            config = AgentConfig.from_file(config_file)

            assert config.agent_json == str(agent_file.resolve())  # Should be absolute path now
            assert config.display_name == "Test Agent"
            assert config.interactive is True
            assert config.required_env_vars == ["VAR1", "VAR2"]

    def test_from_file_nonexistent_file(self) -> None:
        """Test from_file method with nonexistent file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            AgentConfig.from_file(Path("/nonexistent/config.yaml"))
        assert "Agent config not found" in str(exc_info.value)

    def test_from_file_invalid_yaml_content(self) -> None:
        """Test from_file method with invalid YAML content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            config_file = temp_path / "config.yaml"
            config_file.write_text("invalid: yaml: content: [")

            with pytest.raises(yaml.YAMLError):
                AgentConfig.from_file(config_file)

    def test_from_file_non_dict_yaml(self) -> None:
        """Test from_file method with non-dict YAML content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            config_file = temp_path / "config.yaml"
            config_file.write_text("- list\n- content")

            with pytest.raises(ValueError) as exc_info:
                AgentConfig.from_file(config_file)
            assert "expected a mapping" in str(exc_info.value)

    def test_from_file_with_factory_function(self) -> None:
        """Test from_file method with factory function configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            config_data = {
                "agent_factory_function": "module.create_agent",
                "display_name": "Test Agent",
                "required_env_vars": ["API_KEY"],
            }

            config_file = temp_path / "config.yaml"
            config_file.write_text(yaml.dump(config_data))

            config = AgentConfig.from_file(config_file)

            assert config.agent_factory_function == "module.create_agent"
            assert config.display_name == "Test Agent"
            assert config.required_env_vars == ["API_KEY"]
            assert config.agent_json is None
