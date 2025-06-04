import typer

from deepset_mcp.benchmark.runner.config_loader import (
    find_all_test_case_paths,
    load_test_case_by_name,
    load_test_case_from_path,
)
from deepset_mcp.benchmark.runner.models import TestCaseConfig
from deepset_mcp.benchmark.runner.setup_actions import setup_all, setup_test_case
from deepset_mcp.benchmark.runner.teardown_actions import teardown_all, teardown_test_case

tests_app = typer.Typer(help="Commands for setting up and tearing down test-cases.")


@tests_app.command("list")
def list_cases(
    test_dir: str | None = typer.Option(
        None,
        help="Directory where all test-case YAMLs live (`benchmark/tasks/*.yml`).",
    ),
) -> None:
    """List all available test cases stored under `test_dir`."""
    paths = find_all_test_case_paths(test_dir)
    if not paths:
        typer.secho(f"No test-case files found in {test_dir}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    for p in paths:
        typer.echo(f" • {p.stem}")


@tests_app.command("setup")
def create_case(
    test_name: str = typer.Argument(..., help="Test-case name (without .yml)."),
    workspace_name: str = typer.Option(
        "default", "--workspace", "-w", help="Workspace in which to create pipelines and indexes."
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="Explicit DP_API_KEY to use (overrides environment).",
    ),
    test_dir: str | None = typer.Option(
        None,
        help="Directory where test-case YAMLs are stored.",
    ),
) -> None:
    """Load a single test-case by name and create its pipeline + index (if any) on deepset."""
    try:
        test_cfg = load_test_case_by_name(name=test_name, task_dir=test_dir)
    except FileNotFoundError:
        typer.secho(f"Test-case '{test_name}' not found under {test_dir}.", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"Failed to load test-case '{test_name}': {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.secho(f"→ Creating resources for '{test_name}' in '{workspace_name}'…", fg=typer.colors.GREEN)
    try:
        setup_test_case(test_cfg=test_cfg, workspace_name=workspace_name, api_key=api_key)
    except Exception as e:
        typer.secho(f"✘ Failed to set up '{test_name}': {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.secho(f"✔ '{test_name}' ready.", fg=typer.colors.GREEN)


@tests_app.command("setup-all")
def create_all(
    workspace_name: str = typer.Option(
        "default", "--workspace", "-w", help="Workspace in which to create pipelines and indexes."
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="Explicit DP_API_KEY to use (overrides environment).",
    ),
    concurrency: int = typer.Option(
        5,
        "--concurrency",
        "-c",
        help="Maximum number of test-cases to set up in parallel.",
    ),
    test_dir: str | None = typer.Option(
        None,
        help="Directory where test-case YAMLs are stored.",
    ),
) -> None:
    """Load every test-case under `task_dir` and create pipelines + indexes in `workspace_name` in parallel."""
    paths = find_all_test_case_paths(test_dir)
    if not paths:
        typer.secho(f"No test-case files found in {test_dir}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # 1) Load all configs
    test_cfgs: list[TestCaseConfig] = []
    for p in paths:
        try:
            cfg = load_test_case_from_path(path=p)
            test_cfgs.append(cfg)
        except Exception as e:
            typer.secho(f"Skipping '{p.stem}' (load error: {e})", fg=typer.colors.YELLOW)

    if not test_cfgs:
        typer.secho("No valid test-case configs to create.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.secho(
        f"→ Creating {len(test_cfgs)} test-cases in '{workspace_name}' (concurrency={concurrency})…",
        fg=typer.colors.GREEN,
    )
    try:
        setup_all(
            test_cfgs=test_cfgs,
            workspace_name=workspace_name,
            api_key=api_key,
            concurrency=concurrency,
        )
    except Exception as e:
        typer.secho(f"✘ Some test-cases failed during creation: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.secho("✔ All test-cases attempted.", fg=typer.colors.GREEN)


@tests_app.command("teardown")
def delete_case(
    test_name: str = typer.Argument(..., help="Test-case name (without .yml)."),
    workspace_name: str = typer.Option(
        "default", "--workspace", "-w", help="Workspace from which to delete pipelines and indexes."
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="Explicit DP_API_KEY to use (overrides environment).",
    ),
    test_dir: str | None = typer.Option(
        None,
        help="Directory where test-case YAMLs are stored.",
    ),
) -> None:
    """Teardown a single test-case by name and delete its pipeline + index (if any) from deepset."""
    try:
        test_cfg = load_test_case_by_name(name=test_name, task_dir=test_dir)
    except FileNotFoundError:
        typer.secho(f"Test-case '{test_name}' not found under {test_dir}.", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"Failed to load test-case '{test_name}': {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.secho(f"→ Deleting resources for '{test_name}' from '{workspace_name}'…", fg=typer.colors.GREEN)
    try:
        teardown_test_case(test_cfg=test_cfg, workspace_name=workspace_name, api_key=api_key)
    except Exception as e:
        typer.secho(f"✘ Failed to teardown '{test_name}': {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.secho(f"✔ '{test_name}' resources deleted.", fg=typer.colors.GREEN)


@tests_app.command("teardown-all")
def delete_all(
    workspace_name: str = typer.Option(
        "default", "--workspace", "-w", help="Workspace from which to delete pipelines and indexes."
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="Explicit DP_API_KEY to use (overrides environment).",
    ),
    concurrency: int = typer.Option(
        5,
        "--concurrency",
        "-c",
        help="Maximum number of test-cases to teardown in parallel.",
    ),
    test_dir: str | None = typer.Option(
        None,
        help="Directory where test-case YAMLs are stored.",
    ),
) -> None:
    """Teardown every test-case under `task_dir` and delete pipelines and indexes from deepset."""
    paths = find_all_test_case_paths(test_dir)
    if not paths:
        typer.secho(f"No test-case files found in {test_dir}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # 1) Load all configs
    test_cfgs: list[TestCaseConfig] = []
    for p in paths:
        try:
            cfg = load_test_case_from_path(path=p)
            test_cfgs.append(cfg)
        except Exception as e:
            typer.secho(f"Skipping '{p.stem}' (load error: {e})", fg=typer.colors.YELLOW)

    if not test_cfgs:
        typer.secho("No valid test-case configs to delete.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.secho(
        f"→ Deleting {len(test_cfgs)} test-cases from '{workspace_name}' (concurrency={concurrency})…",
        fg=typer.colors.GREEN,
    )
    try:
        teardown_all(
            test_cfgs=test_cfgs,
            workspace_name=workspace_name,
            api_key=api_key,
            concurrency=concurrency,
        )
    except Exception as e:
        typer.secho(f"✘ Some test-cases failed during deletion: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.secho("✔ All test-cases teardown attempted.", fg=typer.colors.GREEN)


def create_tests_app() -> typer.Typer:
    """Create the tests CLI app."""
    return tests_app
