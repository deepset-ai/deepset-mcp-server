import os
from pathlib import Path

import typer
from pydantic import ValidationError

from deepset_mcp.benchmark.runner.config import BenchmarkConfig
from deepset_mcp.benchmark.runner.models import AgentConfig


def override_deepset_env_vars(api_key: str | None, workspace: str | None) -> None:
    """Overrides deepset-specific environment variables."""
    if api_key is not None:
        os.environ["DEEPSET_API_KEY"] = api_key

    if workspace is not None:
        os.environ["DEEPSET_WORKSPACE"] = workspace


def validate_and_setup_configs(
    agent_config: str, test_case_base_dir: str | None, output_dir: str | None
) -> tuple[AgentConfig, BenchmarkConfig]:
    """Validate and setup configurations."""
    # Validate agent config path
    agent_config_path = Path(agent_config)
    if not agent_config_path.exists():
        typer.secho(f"Agent config file not found: {agent_config}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    test_case_base_path = None
    if test_case_base_dir is not None:
        test_case_base_path = Path(test_case_base_dir)
        if not test_case_base_path.exists():
            typer.secho(f"Test case base directory not found: {test_case_base_dir}", fg=typer.colors.RED)
            raise typer.Exit(code=1)

    benchmark_kwargs = {}
    if test_case_base_path is not None:
        benchmark_kwargs["test_case_base_dir"] = test_case_base_path

    if output_dir is not None:
        benchmark_kwargs["output_dir"] = Path(output_dir)

    # Load and validate configurations
    try:
        benchmark_config = BenchmarkConfig(**benchmark_kwargs)  # type: ignore
    except ValidationError as e:
        typer.secho("Configuration error:", fg=typer.colors.RED)
        for error in e.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            typer.secho(f"  {field}: {error['msg']}", fg=typer.colors.RED)
        typer.secho("\nPlease ensure all required environment variables are set", fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)

    try:
        agent_cfg = AgentConfig.from_file(agent_config_path)
    except Exception as e:
        typer.secho(f"Invalid agent config: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    return agent_cfg, benchmark_config
