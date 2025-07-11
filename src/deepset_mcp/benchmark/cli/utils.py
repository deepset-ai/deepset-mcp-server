import os
from pathlib import Path
from typing import Any

import typer
from dotenv import load_dotenv
from pydantic import ValidationError

from deepset_mcp.benchmark.core.config import AgentConfig, BenchmarkConfig


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


# Standardized CLI parameter definitions
def get_standard_api_key_option() -> Any:
    """Get standardized API key option for CLI commands."""
    return typer.Option(
        None,
        "--api-key",
        "-k",
        help="Explicit DEEPSET_API_KEY to use (overrides environment).",
    )


def get_standard_workspace_option(default: str | None = None) -> Any:
    """Get standardized workspace option for CLI commands."""
    return typer.Option(
        default,
        "--workspace",
        "-w",
        help="Deepset workspace name.",
    )


def get_standard_debug_option() -> Any:
    """Get standardized debug option for CLI commands."""
    return typer.Option(
        False,
        "--debug",
        "-d",
        help="Enable debug logging.",
    )


def get_standard_quiet_option() -> Any:
    """Get standardized quiet option for CLI commands."""
    return typer.Option(
        False,
        "--quiet",
        "-q",
        help="Minimal output mode.",
    )


def get_standard_concurrency_option(default: int = 5) -> Any:
    """Get standardized concurrency option for CLI commands."""
    return typer.Option(
        default,
        "--concurrency",
        "-c",
        help="Maximum number of concurrent operations.",
    )


def get_standard_env_file_option() -> Any:
    """Get standardized env file option for CLI commands."""
    return typer.Option(
        None,
        "--env-file",
        "-e",
        help="Path to environment file.",
    )


def get_default_agent_config() -> Any:
    """Get default agent configuration."""
    return typer.Argument(
        str(Path(__file__).parent.parent / "agent_configs/debugging_agent.yml"),
        help="Path to the agent configuration file.",
    )


def load_env_file(env_file: str | None) -> None:
    """Load environment variables from a file if specified."""
    if env_file:
        env_path = Path(env_file)
        if not env_path.exists():
            typer.secho(f"Environment file not found: {env_file}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        load_dotenv(env_path, override=True)
        typer.secho(f"Loaded environment from: {env_file}", fg=typer.colors.BLUE)


# Standardized error handling
def handle_cli_error(error: Exception, operation: str, resource_name: str = "") -> None:
    """
    Handle CLI errors with standardized formatting.

    Args:
        error: The exception that occurred
        operation: The operation that failed (e.g., "create", "delete")
        resource_name: The name of the resource (e.g., "pipeline", "index")
    """
    resource_part = f" {resource_name}" if resource_name else ""
    typer.secho(f"✘ Failed to {operation}{resource_part}: {error}", fg=typer.colors.RED)


def show_cli_success(message: str) -> None:
    """
    Show success message with standardized formatting.

    Args:
        message: The success message to display
    """
    typer.secho(f"✔ {message}", fg=typer.colors.GREEN)


def show_cli_progress(message: str) -> None:
    """
    Show progress message with standardized formatting.

    Args:
        message: The progress message to display
    """
    typer.secho(f"→ {message}", fg=typer.colors.BLUE)


def show_cli_warning(message: str) -> None:
    """
    Show warning message with standardized formatting.

    Args:
        message: The warning message to display
    """
    typer.secho(f"⚠ {message}", fg=typer.colors.YELLOW)


def show_cli_error(message: str) -> None:
    """Show error message with standardized formatting.

    Args:
        message: The error message to display.
    """
    typer.secho(f"✘ {message}", fg=typer.colors.RED)


def setup_deepset_environment(
    api_key: str | None = None, workspace: str | None = None, env_file: str | None = None
) -> tuple[str | None, str | None]:
    """Sets up deepset api key and workspace."""
    load_env_file(env_file)

    resolved_api_key = api_key or os.environ.get("DEEPSET_API_KEY")
    resolved_workspace = workspace or os.environ.get("DEEPSET_WORKSPACE")

    # Override env vars for apps that rely on BenchmarkConfig
    override_deepset_env_vars(api_key=resolved_api_key, workspace=resolved_workspace)

    return resolved_api_key, resolved_workspace
