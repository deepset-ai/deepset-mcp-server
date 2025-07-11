"""Unit tests for the agent loader module."""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from haystack.components.agents.agent import Agent

from deepset_mcp.benchmark.core.agent_loader import (
    _import_factory_from_qualified_name,
    _load_from_json,
    load_agent,
)
from deepset_mcp.benchmark.core.config import AgentConfig, BenchmarkConfig


class TestLoadAgent:
    """Test suite for load_agent function."""

    def test_load_agent_with_factory_function_success(self) -> None:
        """Test successful agent loading with factory function."""
        # Create mock agent and factory function
        mock_agent = Mock(spec=Agent)
        mock_factory = Mock(return_value=mock_agent)

        # Create configs
        agent_config = AgentConfig(
            agent_factory_function="test.module.create_agent",
            agent_json=None,
            display_name="Test Agent",
            interactive=False,
            required_env_vars=["TEST_VAR"],
        )

        with patch.dict(
            os.environ, {"DEEPSET_WORKSPACE": "test_workspace", "DEEPSET_API_KEY": "test_key", "TEST_VAR": "test_value"}
        ):
            benchmark_config = BenchmarkConfig()

        # Mock the import and subprocess calls
        with (
            patch(
                "deepset_mcp.benchmark.core.agent_loader._import_factory_from_qualified_name", return_value=mock_factory
            ),
            patch("subprocess.run") as mock_run,
        ):
            # Mock git command success
            mock_run.return_value.stdout.strip.return_value = "abc123"

            agent, git_hash = load_agent(agent_config, benchmark_config)

            assert agent == mock_agent
            assert git_hash == "abc123"
            mock_factory.assert_called_once_with(benchmark_config)

    def test_load_agent_with_factory_function_interactive(self) -> None:
        """Test agent loading with factory function in interactive mode."""
        mock_agent = Mock(spec=Agent)
        mock_factory = Mock(return_value=mock_agent)

        agent_config = AgentConfig(
            agent_factory_function="test.module.create_agent",
            agent_json=None,
            display_name="Test Agent",
            interactive=False,
            required_env_vars=[],
        )

        with patch.dict(os.environ, {"DEEPSET_WORKSPACE": "test_workspace", "DEEPSET_API_KEY": "test_key"}):
            benchmark_config = BenchmarkConfig()

        with (
            patch(
                "deepset_mcp.benchmark.core.agent_loader._import_factory_from_qualified_name", return_value=mock_factory
            ),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value.stdout.strip.return_value = "abc123"

            agent, git_hash = load_agent(agent_config, benchmark_config, interactive=True)

            assert agent == mock_agent
            assert git_hash == "abc123"
            mock_factory.assert_called_once_with(benchmark_config, interactive=True)

    def test_load_agent_with_json_file_success(self) -> None:
        """Test successful agent loading from JSON file."""
        mock_agent = Mock(spec=Agent)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test JSON file
            agent_file = temp_path / "agent.json"
            agent_data = {"type": "Agent", "components": {}}
            agent_file.write_text(json.dumps(agent_data))

            agent_config = AgentConfig(
                agent_json=str(agent_file),
                agent_factory_function=None,
                display_name="Test Agent",
                interactive=False,
                required_env_vars=["TEST_VAR"],
            )

            with patch.dict(
                os.environ,
                {"DEEPSET_WORKSPACE": "test_workspace", "DEEPSET_API_KEY": "test_key", "TEST_VAR": "test_value"},
            ):
                benchmark_config = BenchmarkConfig()

            with (
                patch("deepset_mcp.benchmark.core.agent_loader._load_from_json", return_value=mock_agent),
                patch("subprocess.run") as mock_run,
            ):
                mock_run.return_value.stdout.strip.return_value = "def456"

                agent, git_hash = load_agent(agent_config, benchmark_config)

                assert agent == mock_agent
                assert git_hash == "def456"

    def test_load_agent_with_json_file_interactive_raises_error(self) -> None:
        """Test that JSON file loading raises error in interactive mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            agent_file = temp_path / "agent.json"
            agent_file.write_text('{"type": "Agent"}')

            agent_config = AgentConfig(
                agent_json=str(agent_file),
                agent_factory_function=None,
                display_name="Test Agent",
                interactive=False,
                required_env_vars=[],
            )

            with patch.dict(os.environ, {"DEEPSET_WORKSPACE": "test_workspace", "DEEPSET_API_KEY": "test_key"}):
                benchmark_config = BenchmarkConfig()

            with pytest.raises(ValueError) as exc_info:
                load_agent(agent_config, benchmark_config, interactive=True)

            assert "Interactive mode is not supported for JSON-based agents" in str(exc_info.value)

    def test_load_agent_missing_required_env_vars(self) -> None:
        """Test that missing required environment variables raise OSError."""
        mock_agent = Mock(spec=Agent)
        mock_factory = Mock(return_value=mock_agent)

        agent_config = AgentConfig(
            agent_factory_function="test.module.create_agent",
            agent_json=None,
            display_name="Test Agent",
            interactive=False,
            required_env_vars=["MISSING_VAR"],
        )

        with patch.dict(os.environ, {"DEEPSET_WORKSPACE": "test_workspace", "DEEPSET_API_KEY": "test_key"}):
            benchmark_config = BenchmarkConfig()

        with (
            patch(
                "deepset_mcp.benchmark.core.agent_loader._import_factory_from_qualified_name", return_value=mock_factory
            ),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value.stdout.strip.return_value = "abc123"

            with pytest.raises(OSError) as exc_info:
                load_agent(agent_config, benchmark_config)

            assert "Required environment variables not set" in str(exc_info.value)
            assert "MISSING_VAR" in str(exc_info.value)

    def test_load_agent_git_command_failure(self) -> None:
        """Test that git command failure results in None git hash."""
        mock_agent = Mock(spec=Agent)
        mock_factory = Mock(return_value=mock_agent)

        agent_config = AgentConfig(
            agent_factory_function="test.module.create_agent",
            agent_json=None,
            display_name="Test Agent",
            interactive=False,
            required_env_vars=[],
        )

        with patch.dict(os.environ, {"DEEPSET_WORKSPACE": "test_workspace", "DEEPSET_API_KEY": "test_key"}):
            benchmark_config = BenchmarkConfig()

        with (
            patch(
                "deepset_mcp.benchmark.core.agent_loader._import_factory_from_qualified_name", return_value=mock_factory
            ),
            patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")),
        ):
            agent, git_hash = load_agent(agent_config, benchmark_config)

            assert agent == mock_agent
            assert git_hash is None

    def test_load_agent_git_not_found(self) -> None:
        """Test that git not found results in None git hash."""
        mock_agent = Mock(spec=Agent)
        mock_factory = Mock(return_value=mock_agent)

        agent_config = AgentConfig(
            agent_factory_function="test.module.create_agent",
            agent_json=None,
            display_name="Test Agent",
            interactive=False,
            required_env_vars=[],
        )

        with patch.dict(os.environ, {"DEEPSET_WORKSPACE": "test_workspace", "DEEPSET_API_KEY": "test_key"}):
            benchmark_config = BenchmarkConfig()

        with (
            patch(
                "deepset_mcp.benchmark.core.agent_loader._import_factory_from_qualified_name", return_value=mock_factory
            ),
            patch("subprocess.run", side_effect=FileNotFoundError("git command not found")),
        ):
            agent, git_hash = load_agent(agent_config, benchmark_config)

            assert agent == mock_agent
            assert git_hash is None

    def test_load_agent_no_source_specified(self) -> None:
        """Test that no agent source raises ValueError."""
        # This test case is mainly for completeness as the validation should prevent this
        # but it's still good to test the fallback behavior
        agent_config = Mock()
        agent_config.agent_factory_function = None
        agent_config.agent_json = None
        agent_config.required_env_vars = []

        with patch.dict(os.environ, {"DEEPSET_WORKSPACE": "test_workspace", "DEEPSET_API_KEY": "test_key"}):
            benchmark_config = BenchmarkConfig()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout.strip.return_value = "abc123"

            with pytest.raises(ValueError) as exc_info:
                load_agent(agent_config, benchmark_config)

            assert "No agent source specified" in str(exc_info.value)


class TestImportFactoryFromQualifiedName:
    """Test suite for _import_factory_from_qualified_name function."""

    def test_import_factory_success(self) -> None:
        """Test successful import of factory function."""
        # Mock the module and function
        mock_module = Mock()
        mock_function = Mock()
        mock_module.create_agent = mock_function

        with patch("importlib.import_module", return_value=mock_module):
            result = _import_factory_from_qualified_name("test.module.create_agent")

            assert result == mock_function

    def test_import_factory_invalid_qualified_name(self) -> None:
        """Test import with invalid qualified name format."""
        with pytest.raises(ValueError) as exc_info:
            _import_factory_from_qualified_name("invalid_name")

        assert "Invalid qualified name format" in str(exc_info.value)
        assert "Expected 'module.path.function_name'" in str(exc_info.value)

    def test_import_factory_module_not_found(self) -> None:
        """Test import with non-existent module."""
        with patch("importlib.import_module", side_effect=ImportError("No module named 'nonexistent'")):
            with pytest.raises(ImportError) as exc_info:
                _import_factory_from_qualified_name("nonexistent.module.function")

            assert "Could not import module 'nonexistent.module'" in str(exc_info.value)

    def test_import_factory_function_not_found(self) -> None:
        """Test import with non-existent function."""
        mock_module = Mock()
        del mock_module.nonexistent_function  # Make sure it doesn't exist

        with patch("importlib.import_module", return_value=mock_module):
            with pytest.raises(AttributeError) as exc_info:
                _import_factory_from_qualified_name("test.module.nonexistent_function")

            assert "Function 'nonexistent_function' not found in module 'test.module'" in str(exc_info.value)

    def test_import_factory_not_callable(self) -> None:
        """Test import with non-callable attribute."""
        mock_module = Mock()
        mock_module.not_callable = "not a function"

        with patch("importlib.import_module", return_value=mock_module):
            with pytest.raises(ValueError) as exc_info:
                _import_factory_from_qualified_name("test.module.not_callable")

            assert "'test.module.not_callable' is not callable" in str(exc_info.value)


class TestLoadFromJson:
    """Test suite for _load_from_json function."""

    def test_load_from_json_success(self) -> None:
        """Test successful loading from JSON file."""
        mock_agent = Mock(spec=Agent)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test JSON file
            agent_file = temp_path / "agent.json"
            agent_data = {"type": "Agent", "components": {}}
            agent_file.write_text(json.dumps(agent_data))

            with patch.object(Agent, "from_dict", return_value=mock_agent) as mock_from_dict:
                result = _load_from_json(str(agent_file))

                assert result == mock_agent
                mock_from_dict.assert_called_once_with(agent_data)

    def test_load_from_json_file_not_found(self) -> None:
        """Test loading from non-existent JSON file."""
        with pytest.raises(FileNotFoundError):
            _load_from_json("/nonexistent/file.json")

    def test_load_from_json_invalid_json(self) -> None:
        """Test loading from invalid JSON file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            agent_file = temp_path / "agent.json"
            agent_file.write_text("invalid json content {")

            with pytest.raises(json.JSONDecodeError):
                _load_from_json(str(agent_file))

    def test_load_from_json_agent_from_dict_failure(self) -> None:
        """Test loading when Agent.from_dict fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            agent_file = temp_path / "agent.json"
            agent_data = {"invalid": "agent_data"}
            agent_file.write_text(json.dumps(agent_data))

            with patch.object(Agent, "from_dict", side_effect=Exception("Invalid agent data")):
                with pytest.raises(Exception) as exc_info:
                    _load_from_json(str(agent_file))

                assert "Invalid agent data" in str(exc_info.value)
