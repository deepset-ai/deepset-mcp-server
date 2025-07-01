import importlib
import json
import os
import subprocess
from collections.abc import Callable
from typing import cast

from haystack.components.agents.agent import Agent

from deepset_mcp.benchmark.runner.config import BenchmarkConfig
from deepset_mcp.benchmark.runner.models import AgentConfig


def load_agent(
    config: AgentConfig,
    benchmark_config: BenchmarkConfig,
    interactive: bool = False,
) -> tuple[Agent, str | None]:
    """
    Load an agent based on the configuration.

    This function:
    - Loads the agent from either qualified name or JSON file
    - Checks required environment variables (for qualified name approach)
    - Collects metadata (timestamp, git commit hash)

    Args:
        config: AgentConfig instance specifying how to load the agent
        benchmark_config: BenchmarkConfig instance specifying the benchmark configuration.
        interactive: Whether to load the agent in interactive mode.

    Returns:
        LoadedAgent containing the agent instance and metadata

    Raises:
        ImportError: If qualified function cannot be imported
        AttributeError: If function doesn't exist in module
        ValueError: If function is not callable or doesn't return proper tuple
        FileNotFoundError: If JSON file cannot be found
        EnvironmentError: If required environment variables are not set
        json.JSONDecodeError: If JSON file is invalid
    """
    # Get git commit hash
    git_commit_hash = None
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True, cwd=os.getcwd()
        )
        git_commit_hash = result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Git not available or not in a git repo
        pass

    # Load the agent
    if config.agent_factory_function:
        agent_func = _import_factory_from_qualified_name(config.agent_factory_function)
        if interactive:
            agent = agent_func(
                benchmark_config,
                interactive=True,
            )
        else:
            agent = agent_func(benchmark_config)
    elif config.agent_json:
        if interactive:
            raise ValueError("Interactive mode is not supported for JSON-based agents.")
        agent = _load_from_json(config.agent_json)
    else:
        # This should never happen due to validation, but just in case
        raise ValueError("No agent source specified")

    is_complete, missing = benchmark_config.check_required_env_vars(config.required_env_vars)

    if not is_complete:
        raise OSError(f"Required environment variables not set. Missing: {', '.join(missing)}.")

    return agent, git_commit_hash


def _import_factory_from_qualified_name(qualified_name: str) -> Callable[..., Agent]:
    """Load agent from qualified function name."""
    try:
        module_path, function_name = qualified_name.rsplit(".", 1)
    except ValueError as e:
        raise ValueError(
            f"Invalid qualified name format: '{qualified_name}'. Expected 'module.path.function_name'"
        ) from e

    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        raise ImportError(f"Could not import module '{module_path}': {e}") from e

    try:
        get_agent_func = getattr(module, function_name)
    except AttributeError as e:
        raise AttributeError(f"Function '{function_name}' not found in module '{module_path}'") from e

    if not callable(get_agent_func):
        raise ValueError(f"'{qualified_name}' is not callable")

    return cast(Callable[..., Agent], get_agent_func)


def _load_from_json(json_path: str) -> Agent:
    """Load agent from JSON file."""
    with open(json_path, encoding="utf-8") as f:
        agent_dict = json.load(f)

    return Agent.from_dict(agent_dict)
