"""Updated CLI agent commands using the new refactored architecture."""

import asyncio
from pathlib import Path

import typer
from pydantic import ValidationError

from deepset_mcp.benchmark.cli.repl import run_repl_session
from deepset_mcp.benchmark.cli.utils import (
    get_default_agent_config,
    get_standard_api_key_option,
    get_standard_concurrency_option,
    get_standard_debug_option,
    get_standard_env_file_option,
    get_standard_quiet_option,
    get_standard_workspace_option,
    load_env_file,
    setup_deepset_environment,
    show_cli_error,
    show_cli_progress,
    show_cli_success,
    show_cli_warning,
    validate_and_setup_configs,
)
from deepset_mcp.benchmark.core.config import AgentConfig, BenchmarkConfig
from deepset_mcp.benchmark.executors.benchmark_executor import create_benchmark_executor_from_config

agent_app = typer.Typer(help="Commands for running agents against test cases (refactored).")


@agent_app.command("run")
def run_agent_single(
    agent_config: str = get_default_agent_config(),
    test_case: str = typer.Argument(..., help="Name of the test case to run."),
    # These are used in the deepset_environment_setup
    workspace: str | None = get_standard_workspace_option(),
    api_key: str | None = get_standard_api_key_option(),
    env_file: str | None = get_standard_env_file_option(),
    output_dir: str | None = typer.Option(None, "--output-dir", "-o", help="Directory to save results."),
    test_case_base_dir: str | None = typer.Option(None, "--test-base-dir", help="Base directory for test cases."),
    streaming: bool = typer.Option(True, "--streaming/--no-streaming", help="Enable streaming output."),
    quiet: bool = get_standard_quiet_option(),
    debug: bool = get_standard_debug_option(),
) -> None:
    """Run an agent against a single test case."""
    setup_deepset_environment(api_key=api_key, workspace=workspace, env_file=env_file)

    # Load and validate configurations
    agent_cfg, benchmark_cfg = validate_and_setup_configs(
        agent_config=agent_config,
        test_case_base_dir=test_case_base_dir,
        output_dir=output_dir,
    )

    # Update benchmark config with test case base dir if provided
    if test_case_base_dir:
        benchmark_cfg.test_case_base_dir = Path(test_case_base_dir)

    if not quiet:
        show_cli_progress(message=f"→ Running agent '{agent_cfg.display_name}' on test case '{test_case}'")

    # Create executor using factory
    executor = create_benchmark_executor_from_config(
        agent_config_path=agent_config,
        benchmark_config=benchmark_cfg,
        streaming_enabled=streaming,
        quiet=quiet,
        debug=debug,
    )

    # Run test case
    result = asyncio.run(
        executor.run_single_test_with_cleanup(
            test_case_name=test_case,
            streaming_enabled=streaming,
            output_dir=Path(benchmark_cfg.output_dir) if benchmark_cfg.output_dir else None,
        )
    )

    # Handle result
    if result["status"] == "success":
        if not quiet:
            show_cli_success(message="Test completed!")

        # Check cleanup status
        if result.get("cleanup_status") == "error":
            show_cli_warning(message=f"Cleanup failed: {result.get('cleanup_error')}")
    else:
        show_cli_error(message=f"Test failed: {result.get('error')}")
        raise typer.Exit(code=1)


@agent_app.command("run-all")
def run_agent_all(
    agent_config: str = get_default_agent_config(),
    workspace: str | None = get_standard_workspace_option(),
    api_key: str | None = get_standard_api_key_option(),
    env_file: str | None = get_standard_env_file_option(),
    output_dir: str | None = typer.Option(None, "--output-dir", "-o", help="Directory to save results."),
    test_case_base_dir: str | None = typer.Option(None, "--test-base-dir", help="Base directory for test cases."),
    concurrency: int = get_standard_concurrency_option(default=1),
    streaming: bool = typer.Option(True, "--streaming/--no-streaming", help="Enable streaming output."),
    quiet: bool = get_standard_quiet_option(),
    debug: bool = get_standard_debug_option(),
) -> None:
    """Run an agent against all available test cases."""
    setup_deepset_environment(api_key=api_key, workspace=workspace, env_file=env_file)
    # Load and validate configurations
    agent_cfg, benchmark_cfg = validate_and_setup_configs(
        agent_config=agent_config,
        test_case_base_dir=test_case_base_dir,
        output_dir=output_dir,
    )

    # Update benchmark config with test case base dir if provided
    if test_case_base_dir:
        benchmark_cfg.test_case_base_dir = Path(test_case_base_dir)

    if not quiet:
        show_cli_progress(
            f"Running agent '{agent_cfg.display_name}' on all test cases (concurrency={concurrency})",
        )

    # Create executor using factory
    executor = create_benchmark_executor_from_config(
        agent_config_path=agent_config,
        benchmark_config=benchmark_cfg,
        streaming_enabled=streaming,
        quiet=quiet,
        debug=debug,
    )

    # Find all test cases
    test_cases = executor.benchmark_repository.find_all_test_cases(benchmark_cfg.test_case_base_dir)
    test_case_names = [tc.name for tc in test_cases]

    if not test_case_names:
        show_cli_warning(f"No test cases found in {benchmark_cfg.test_case_base_dir}")
        return

    # Run all test cases
    results, summary = asyncio.run(
        executor.run_multiple_tests(
            test_case_names=test_case_names,
            streaming_enabled=streaming,
            output_dir=Path(benchmark_cfg.output_dir) if benchmark_cfg.output_dir else None,
            concurrency=concurrency,
        )
    )

    # The output handler will have shown the summary, so just handle exit code
    if summary["failed_tests"] > 0:
        raise typer.Exit(code=1)


@agent_app.command("check-env")
def check_environment(
    agent_config: str = get_default_agent_config(),
    env_file: str | None = get_standard_env_file_option(),
) -> None:
    """Check if environment variables are configured correctly for an agent to run."""
    load_env_file(env_file)

    # Try to load base config
    try:
        benchmark_config = BenchmarkConfig()
        show_cli_success("Base configuration loaded")
    except ValidationError as e:
        typer.secho("✗ Base configuration missing:", fg=typer.colors.RED)
        for error in e.errors():
            field = str(error["loc"][0]) if error["loc"] else "unknown"
            typer.secho(f"  - {field.upper()}", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Load agent config
    try:
        agent_cfg = AgentConfig.from_file(Path(agent_config))
    except Exception as e:
        show_cli_error(f"Failed to load agent config: {e}")
        raise typer.Exit(1)

    typer.secho(f"\nEnvironment check for: {agent_cfg.display_name}", fg=typer.colors.BLUE)
    typer.secho("=" * 50, fg=typer.colors.BLUE)

    # Show core configuration
    typer.secho("\nCore configuration:", fg=typer.colors.YELLOW)
    typer.secho(f"  ✓ DEEPSET_WORKSPACE = {benchmark_config.deepset_workspace}", fg=typer.colors.GREEN)
    typer.secho(f"  ✓ DEEPSET_API_KEY = {'*' * 8}...", fg=typer.colors.GREEN)

    # Try to load agent to discover requirements
    typer.secho("\nAgent requirements:", fg=typer.colors.YELLOW)
    is_valid, missing = benchmark_config.check_required_env_vars(agent_cfg.required_env_vars)

    if not is_valid:
        typer.secho(f"\n✗ Missing required variables: {', '.join(missing)}", fg=typer.colors.RED)


@agent_app.command("validate-config")
def validate_agent_config(
    agent_config: str = typer.Argument(..., help="Path to agent configuration file to validate."),
) -> None:
    """Validate an agent configuration file."""
    agent_config_path = Path(agent_config)
    if not agent_config_path.exists():
        show_cli_error(f"Agent config file not found: {agent_config}")
        raise typer.Exit(code=1)

    try:
        config = AgentConfig.from_file(agent_config_path)
        show_cli_success("Agent config is valid")
        typer.secho(f"  Display name: {config.display_name}", fg=typer.colors.BLUE)

        if config.agent_factory_function:
            typer.secho(f"  Type: Function-based ({config.agent_factory_function})", fg=typer.colors.BLUE)
        elif config.agent_json:
            typer.secho(f"  Type: JSON-based ({config.agent_json})", fg=typer.colors.BLUE)

        if config.required_env_vars:
            typer.secho(f"  Declared env vars: {', '.join(config.required_env_vars)}", fg=typer.colors.BLUE)

    except Exception as e:
        show_cli_error(f"Invalid agent config: {e}")
        raise typer.Exit(code=1)


@agent_app.command("chat")
def chat_with_agent(
    agent_config: str = get_default_agent_config(),
    workspace: str | None = get_standard_workspace_option(),
    api_key: str | None = get_standard_api_key_option(),
    env_file: str | None = get_standard_env_file_option(),
) -> None:
    """Start an interactive REPL session with an agent."""
    setup_deepset_environment(api_key=api_key, workspace=workspace, env_file=env_file)
    agent_cfg, benchmark_cfg = validate_and_setup_configs(
        agent_config=agent_config,
        test_case_base_dir=None,
        output_dir=None,
    )

    run_repl_session(agent_config=agent_cfg, benchmark_config=benchmark_cfg)


def create_agents_app() -> typer.Typer:
    """Create the agents CLI app with new architecture."""
    return agent_app
