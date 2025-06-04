from pathlib import Path

import typer
from dotenv import load_dotenv
from pydantic import ValidationError

from deepset_mcp.benchmark.runner.agent_benchmark_runner import run_agent_benchmark
from deepset_mcp.benchmark.runner.cli_utils import override_deepset_env_vars, validate_and_setup_configs
from deepset_mcp.benchmark.runner.config import BenchmarkConfig
from deepset_mcp.benchmark.runner.models import AgentConfig


def load_env_file(env_file: str | None) -> None:
    """Load environment variables from a file if specified."""
    if env_file:
        env_path = Path(env_file)
        if not env_path.exists():
            typer.secho(f"Environment file not found: {env_file}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        load_dotenv(env_path, override=True)
        typer.secho(f"Loaded environment from: {env_file}", fg=typer.colors.BLUE)
    else:
        # Try to load default .env file
        default_env_path = Path(__file__).parent / ".env"
        if default_env_path.exists():
            load_dotenv()
            typer.secho("Loaded default .env file", fg=typer.colors.BLUE)


agent_app = typer.Typer(help="Commands for running agents against test cases.")


@agent_app.command("run")
def run_agent_single(
    agent_config: str = typer.Argument(..., help="Path to agent configuration file (YAML)."),
    test_case: str = typer.Argument(..., help="Name of the test case to run."),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Override Deepset workspace."),
    api_key: str | None = typer.Option(None, "--api-key", "-k", help="Override Deepset API key."),
    env_file: str | None = typer.Option(None, "--env-file", "-e", help="Path to environment file."),
    output_dir: str | None = typer.Option(None, "--output-dir", "-o", help="Directory to save results."),
    test_case_base_dir: str | None = typer.Option(None, "--test-base-dir", help="Base directory for test cases."),
) -> None:
    """Run an agent against a single test case."""
    load_env_file(env_file)
    override_deepset_env_vars(workspace=workspace, api_key=api_key)
    agent_cfg, benchmark_cfg = validate_and_setup_configs(
        agent_config=agent_config,
        test_case_base_dir=test_case_base_dir,
        output_dir=output_dir,
    )

    typer.secho(f"→ Running agent '{agent_cfg.display_name}' on test case '{test_case}'", fg=typer.colors.GREEN)

    try:
        results = run_agent_benchmark(
            agent_config=agent_cfg,
            test_case_name=test_case,
            benchmark_config=benchmark_cfg,
        )

        result = results[0]

        if result["status"] == "success":
            typer.secho("✔ Test completed successfully!", fg=typer.colors.GREEN)
            typer.secho(f"  Results saved to: {result['output_dir']}", fg=typer.colors.BLUE)

            # Show basic stats
            if "processed_data" in result:
                stats = result["processed_data"]["messages"]["stats"]
                typer.secho(f"  Tool calls: {stats['total_tool_calls']}", fg=typer.colors.BLUE)
                typer.secho(f"  Prompt tokens: {stats['total_prompt_tokens']}", fg=typer.colors.BLUE)
                typer.secho(f"  Completion tokens: {stats['total_completion_tokens']}", fg=typer.colors.BLUE)
                typer.secho(f"  Model: {stats['model']}", fg=typer.colors.BLUE)

                # Show validation results
                validation = result["processed_data"]["validation"]
                typer.secho(f"  Pre-validation: {validation['pre_validation']}", fg=typer.colors.BLUE)
                typer.secho(f"  Post-validation: {validation['post_validation']}", fg=typer.colors.BLUE)
        else:
            typer.secho(f"✘ Test failed: {result['error']}", fg=typer.colors.RED)
            raise typer.Exit(code=1)

        # Check cleanup status
        if result.get("cleanup_status") == "error":
            typer.secho(f"⚠ Cleanup failed: {result.get('cleanup_error')}", fg=typer.colors.YELLOW)

    except Exception as e:
        typer.secho(f"✘ Error running benchmark: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@agent_app.command("run-all")
def run_agent_all(
    agent_config: str = typer.Argument(..., help="Path to agent configuration file (YAML)."),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Override Deepset workspace."),
    api_key: str | None = typer.Option(None, "--api-key", "-k", help="Override Deepset API key."),
    env_file: str | None = typer.Option(None, "--env-file", "-e", help="Path to environment file."),
    output_dir: str | None = typer.Option(None, "--output-dir", "-o", help="Directory to save results."),
    test_case_base_dir: str | None = typer.Option(None, "--test-base-dir", help="Base directory for test cases."),
    concurrency: int = typer.Option(1, "--concurrency", "-c", help="Number of concurrent test runs."),
) -> None:
    """Run an agent against all available test cases."""
    load_env_file(env_file)
    override_deepset_env_vars(workspace=workspace, api_key=api_key)
    agent_cfg, benchmark_cfg = validate_and_setup_configs(
        agent_config=agent_config,
        test_case_base_dir=test_case_base_dir,
        output_dir=output_dir,
    )

    typer.secho(
        f"→ Running agent '{agent_cfg.display_name}' on all test cases (concurrency={concurrency})",
        fg=typer.colors.GREEN,
    )

    try:
        results = run_agent_benchmark(
            agent_config=agent_cfg,
            test_case_name=None,  # Run all
            benchmark_config=benchmark_cfg,
            concurrency=concurrency,
        )

        # Summarize results
        successful = [r for r in results if r["status"] == "success"]
        failed = [r for r in results if r["status"] == "error"]

        typer.secho(f"\n✔ Completed {len(results)} test cases", fg=typer.colors.GREEN)
        typer.secho(f"  Successful: {len(successful)}", fg=typer.colors.GREEN)
        typer.secho(f"  Failed: {len(failed)}", fg=typer.colors.RED if failed else typer.colors.GREEN)

        if successful:
            # Calculate aggregate stats
            total_tool_calls = sum(r["processed_data"]["messages"]["stats"]["total_tool_calls"] for r in successful)
            total_prompt_tokens = sum(
                r["processed_data"]["messages"]["stats"]["total_prompt_tokens"] for r in successful
            )
            total_completion_tokens = sum(
                r["processed_data"]["messages"]["stats"]["total_completion_tokens"] for r in successful
            )

            typer.secho("\nAggregate Statistics:", fg=typer.colors.BLUE)
            typer.secho(f"  Total tool calls: {total_tool_calls}", fg=typer.colors.BLUE)
            typer.secho(f"  Total prompt tokens: {total_prompt_tokens}", fg=typer.colors.BLUE)
            typer.secho(f"  Total completion tokens: {total_completion_tokens}", fg=typer.colors.BLUE)

            # Show first successful result's output directory as an example
            example_output = successful[0]["output_dir"]
            base_dir = str(Path(example_output).parent)
            typer.secho(f"  Results saved to: {base_dir}", fg=typer.colors.BLUE)

        if failed:
            typer.secho("\nFailed test cases:", fg=typer.colors.RED)
            for result in failed:
                typer.secho(f"  • {result['test_case']}: {result['error']}", fg=typer.colors.RED)

        # Check for cleanup issues
        cleanup_issues = [r for r in results if r.get("cleanup_status") == "error"]
        if cleanup_issues:
            typer.secho(f"\n⚠ {len(cleanup_issues)} test cases had cleanup issues", fg=typer.colors.YELLOW)

        # Exit with error code if any tests failed
        if failed:
            raise typer.Exit(code=1)

    except Exception as e:
        typer.secho(f"✘ Error running benchmarks: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@agent_app.command("check-env")
def check_environment(
    agent_config: str = typer.Argument(..., help="Path to agent configuration file."),
    env_file: str | None = typer.Option(None, "--env-file", "-e", help="Path to environment file."),
) -> None:
    """Check if environment variables are configured correctly for an agent to run."""
    load_env_file(env_file)

    # Try to load base config
    try:
        benchmark_config = BenchmarkConfig()
        typer.secho("✓ Base configuration loaded", fg=typer.colors.GREEN)
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
        typer.secho(f"✗ Failed to load agent config: {e}", fg=typer.colors.RED)
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
        typer.secho(f"Agent config file not found: {agent_config}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    try:
        config = AgentConfig.from_file(agent_config_path)
        typer.secho("✔ Agent config is valid", fg=typer.colors.GREEN)
        typer.secho(f"  Display name: {config.display_name}", fg=typer.colors.BLUE)

        if config.agent_factory_function:
            typer.secho(f"  Type: Function-based ({config.agent_factory_function})", fg=typer.colors.BLUE)
        elif config.agent_json:
            typer.secho(f"  Type: JSON-based ({config.agent_json})", fg=typer.colors.BLUE)

        if config.required_env_vars:
            typer.secho(f"  Declared env vars: {', '.join(config.required_env_vars)}", fg=typer.colors.BLUE)

    except Exception as e:
        typer.secho(f"✘ Invalid agent config: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


def create_agents_app() -> typer.Typer:
    """Create the agents CLI app."""
    return agent_app
