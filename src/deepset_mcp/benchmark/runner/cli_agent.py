from pathlib import Path

import typer
from dotenv import load_dotenv
from pydantic import ValidationError

from deepset_mcp.benchmark.runner.agent_benchmark_runner import run_agent_benchmark
from deepset_mcp.benchmark.runner.cli_utils import override_deepset_env_vars, validate_and_setup_configs
from deepset_mcp.benchmark.runner.config import BenchmarkConfig
from deepset_mcp.benchmark.runner.models import AgentConfig
from deepset_mcp.benchmark.runner.repl import run_repl_session


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
            typer.secho("Loaded default .env file.", fg=typer.colors.BLUE)


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
        results, _ = run_agent_benchmark(
            agent_config=agent_cfg, test_case_name=test_case, benchmark_config=benchmark_cfg, streaming=True
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
                typer.secho(f"  Pre-validation: {validation['pre_validation'] or 'N/A'}", fg=typer.colors.BLUE)
                typer.secho(f"  Post-validation: {validation['post_validation'] or 'N/A'}", fg=typer.colors.BLUE)
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
        results, summary = run_agent_benchmark(
            agent_config=agent_cfg,
            test_case_name=None,  # Run all
            benchmark_config=benchmark_cfg,
            concurrency=concurrency,
            streaming=True,
        )

        # Display summary statistics
        typer.secho("\n📊 BENCHMARK SUMMARY", fg=typer.colors.BRIGHT_BLUE, bold=True)
        typer.secho("=" * 50, fg=typer.colors.BLUE)

        typer.secho(f"Tests Completed: {summary['tests_completed']}", fg=typer.colors.GREEN)
        typer.secho(
            f"Tests Failed: {summary['tests_failed']}",
            fg=typer.colors.RED if summary["tests_failed"] > 0 else typer.colors.GREEN,
        )
        typer.secho(
            f"Pass Rate: {summary['pass_rate_percent']:.1f}%",
            fg=typer.colors.GREEN
            if summary["pass_rate_percent"] > 80
            else typer.colors.YELLOW
            if summary["pass_rate_percent"] > 50
            else typer.colors.RED,
        )
        typer.secho(
            f"Fail Rate: {summary['fail_rate_percent']:.1f}%",
            fg=typer.colors.RED
            if summary["fail_rate_percent"] > 20
            else typer.colors.YELLOW
            if summary["fail_rate_percent"] > 0
            else typer.colors.GREEN,
        )

        typer.secho("\nToken Usage:", fg=typer.colors.CYAN)
        typer.secho(f"  Prompt Tokens: {summary['total_prompt_tokens']:,}", fg=typer.colors.CYAN)
        typer.secho(f"  Completion Tokens: {summary['total_completion_tokens']:,}", fg=typer.colors.CYAN)
        typer.secho(
            f"  Total Tokens: {summary['total_prompt_tokens'] + summary['total_completion_tokens']:,}",
            fg=typer.colors.CYAN,
        )
        typer.secho(f"  Avg Tool Calls: {summary['avg_tool_calls']:.1f}", fg=typer.colors.CYAN)

        # Display detailed results table
        if results:
            typer.secho("\n📋 DETAILED RESULTS", fg=typer.colors.BRIGHT_BLUE, bold=True)
            typer.secho("=" * 120, fg=typer.colors.BLUE)

            # Table header
            header = (
                f"{'Test Case':<25} {'Status':<8} {'Pre':<5} {'Post':<5} {'Tools':<6} {'P.Tokens':<9} "
                f"{'C.Tokens':<9} {'Cleanup':<8}"
            )
            typer.secho(header, fg=typer.colors.BRIGHT_WHITE, bold=True)
            typer.secho("-" * 120, fg=typer.colors.BLUE)

            # Table rows
            for result in results:
                test_case = result["test_case"][:24]  # Truncate long names
                status = result["status"]

                if status == "success":
                    processed_data = result["processed_data"]
                    stats = processed_data["messages"]["stats"]
                    validation = processed_data["validation"]

                    pre_val = validation["pre_validation"] or "N/A"
                    post_val = validation["post_validation"] or "N/A"
                    tool_calls = stats["total_tool_calls"]
                    prompt_tokens = stats["total_prompt_tokens"]
                    completion_tokens = stats["total_completion_tokens"]
                    cleanup_status = result.get("cleanup_status", "N/A")

                    # Color coding for validation
                    pre_color = (
                        typer.colors.RED
                        if pre_val == "FAIL"
                        else typer.colors.GREEN
                        if pre_val == "PASS"
                        else typer.colors.WHITE
                    )
                    post_color = (
                        typer.colors.GREEN
                        if post_val == "PASS"
                        else typer.colors.RED
                        if post_val == "FAIL"
                        else typer.colors.WHITE
                    )
                    cleanup_color = (
                        typer.colors.GREEN
                        if cleanup_status == "success"
                        else typer.colors.RED
                        if cleanup_status == "error"
                        else typer.colors.WHITE
                    )

                    # Format the row
                    row = f"{test_case:<25} "
                    typer.echo(row, nl=False)
                    typer.secho("SUCCESS ", fg=typer.colors.GREEN, nl=False)
                    typer.secho(f"{pre_val:<5} ", fg=pre_color, nl=False)
                    typer.secho(f"{post_val:<5} ", fg=post_color, nl=False)
                    typer.echo(f"{tool_calls:<6} {prompt_tokens:<9} {completion_tokens:<9} ", nl=False)
                    typer.secho(f"{cleanup_status:<8}", fg=cleanup_color)

                else:
                    # Error case
                    error_msg = result.get("error", "Unknown error")[:30]
                    cleanup_status = result.get("cleanup_status", "N/A")
                    cleanup_color = (
                        typer.colors.GREEN
                        if cleanup_status == "success"
                        else typer.colors.RED
                        if cleanup_status == "error"
                        else typer.colors.WHITE
                    )

                    row = f"{test_case:<25} "
                    typer.echo(row, nl=False)
                    typer.secho(f"ERROR   {error_msg}", fg=typer.colors.RED, nl=False)
                    typer.echo(f"{'N/A':<5} {'N/A':<5} {'N/A':<6} {'N/A':<9} {'N/A':<9} ", nl=False)
                    typer.secho(f"{cleanup_status:<8}", fg=cleanup_color)

        # Show output directory
        if results and results[0].get("output_dir"):
            example_output = results[0]["output_dir"]
            base_dir = str(Path(example_output).parent)
            typer.secho(f"\n💾 Results saved to: {base_dir}", fg=typer.colors.MAGENTA)

        # Show failed test details if any
        failed_results = [r for r in results if r["status"] == "error"]
        if failed_results:
            typer.secho("\n❌ FAILED TESTS DETAILS", fg=typer.colors.RED, bold=True)
            typer.secho("-" * 50, fg=typer.colors.RED)
            for result in failed_results:
                typer.secho(f"  • {result['test_case']}: {result.get('error', 'Unknown error')}", fg=typer.colors.RED)

        # Check for cleanup issues
        cleanup_issues = [r for r in results if r.get("cleanup_status") == "error"]
        if cleanup_issues:
            typer.secho("\n⚠️  CLEANUP ISSUES", fg=typer.colors.YELLOW, bold=True)
            typer.secho("-" * 50, fg=typer.colors.YELLOW)
            for result in cleanup_issues:
                typer.secho(
                    f"  • {result['test_case']}: {result.get('cleanup_error', 'Unknown cleanup error')}",
                    fg=typer.colors.YELLOW,
                )

        typer.secho("\n✅ Benchmark completed successfully!", fg=typer.colors.GREEN, bold=True)

        # Exit with error code if any tests failed
        if summary["tests_failed"] > 0:
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


@agent_app.command("chat")
def chat_with_agent(
    agent_config: str = typer.Argument(
        default=str(Path(__file__).parent.parent / "agent_configs/debugging_agent.yml"),
        help="Path to agent configuration file (YAML).",
    ),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Override Deepset workspace."),
    api_key: str | None = typer.Option(None, "--api-key", "-k", help="Override Deepset API key."),
    env_file: str | None = typer.Option(None, "--env-file", "-e", help="Path to environment file."),
) -> None:
    """Start an interactive REPL session with an agent."""
    load_env_file(env_file)
    override_deepset_env_vars(workspace=workspace, api_key=api_key)
    agent_cfg, benchmark_cfg = validate_and_setup_configs(
        agent_config=agent_config,
        test_case_base_dir=None,
        output_dir=None,
    )

    try:
        run_repl_session(agent_config=agent_cfg, benchmark_config=benchmark_cfg)
    except Exception as e:
        typer.secho(f"✘ Error during REPL session: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


def create_agents_app() -> typer.Typer:
    """Create the agents CLI app."""
    return agent_app
