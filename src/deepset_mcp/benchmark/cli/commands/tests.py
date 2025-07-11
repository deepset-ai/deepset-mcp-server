import typer

from deepset_mcp.benchmark.cli.utils import (
    get_standard_api_key_option,
    get_standard_concurrency_option,
    get_standard_env_file_option,
    get_standard_workspace_option,
    setup_deepset_environment,
    show_cli_error,
)
from deepset_mcp.benchmark.core.config import TestCaseConfig
from deepset_mcp.benchmark.core.repository import FileSystemBenchmarkRepository
from deepset_mcp.benchmark.core.services import get_deepset_resource_service

tests_app = typer.Typer(help="Commands for setting up and tearing down test-cases.")


@tests_app.command("list")
def list_cases(
    test_dir: str | None = typer.Option(
        None,
        help="Directory where all test-case YAMLs live (`benchmark/tasks/*.yml`).",
    ),
) -> None:
    """List all available test cases stored under `test_dir`."""
    repository = FileSystemBenchmarkRepository()
    paths = repository.find_all_test_case_paths(test_dir)
    if not paths:
        typer.secho(f"No test-case files found in {test_dir}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    for p in paths:
        typer.echo(f" • {p.stem}")


@tests_app.command("setup")
def create_case(
    test_name: str = typer.Argument(..., help="Test-case name (without .yml)."),
    workspace_name: str = get_standard_workspace_option(),
    api_key: str | None = get_standard_api_key_option(),
    env_file: str | None = get_standard_env_file_option(),
    test_dir: str | None = typer.Option(
        None,
        help="Directory where test-case YAMLs are stored.",
    ),
) -> None:
    """Load a single test-case by name and create its pipeline + index (if any) on deepset."""
    resolved_api_key, resolved_workspace = setup_deepset_environment(
        api_key=api_key, workspace=workspace_name, env_file=env_file
    )

    if resolved_workspace is None:
        show_cli_error(
            "You need to provide either 'workspace_name' or set the 'DEEPSET_WORKSPACE' environment variable."
        )
        raise typer.Exit(code=1)

    if resolved_api_key is None:
        show_cli_error("You need to provide either 'api_key' or set the 'DEEPSET_API_KEY' environment variable.'")
        raise typer.Exit(code=1)

    repository = FileSystemBenchmarkRepository()
    test_cfg = repository.load_test_case_by_name(name=test_name, task_dir=test_dir)

    typer.secho(f"→ Creating resources for '{test_name}' in '{resolved_workspace}'…", fg=typer.colors.GREEN)
    deepset_service = get_deepset_resource_service(api_key=resolved_api_key)
    deepset_service.setup_test_resources_sync(test_case=test_cfg, workspace=resolved_workspace)

    typer.secho(f"✔ '{test_name}' ready.", fg=typer.colors.GREEN)


@tests_app.command("setup-all")
def create_all(
    workspace_name: str | None = get_standard_workspace_option(),
    api_key: str | None = get_standard_api_key_option(),
    env_file: str | None = get_standard_env_file_option(),
    concurrency: int = get_standard_concurrency_option(),
    test_dir: str | None = typer.Option(
        None,
        help="Directory where test-case YAMLs are stored.",
    ),
) -> None:
    """Load every test-case under `task_dir` and create pipelines + indexes in `workspace_name` in parallel."""
    resolved_api_key, resolved_workspace = setup_deepset_environment(
        api_key=api_key, workspace=workspace_name, env_file=env_file
    )

    if resolved_workspace is None:
        show_cli_error(
            "You need to provide either 'workspace_name' or set the 'DEEPSET_WORKSPACE' environment variable."
        )
        raise typer.Exit(code=1)

    if resolved_api_key is None:
        show_cli_error("You need to provide either 'api_key' or set the 'DEEPSET_API_KEY' environment variable.'")
        raise typer.Exit(code=1)

    repository = FileSystemBenchmarkRepository()
    paths = repository.find_all_test_case_paths(test_dir)
    if not paths:
        typer.secho(f"No test-case files found in {test_dir}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # 1) Load all configs
    test_cfgs: list[TestCaseConfig] = []
    for p in paths:
        try:
            cfg = repository.load_test_case_from_path(path=p)
            test_cfgs.append(cfg)
        except Exception as e:
            typer.secho(f"Skipping '{p.stem}' (load error: {e})", fg=typer.colors.YELLOW)

    if not test_cfgs:
        typer.secho("No valid test-case configs to create.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.secho(
        f"→ Creating {len(test_cfgs)} test-cases in '{resolved_workspace}' (concurrency={concurrency})…",
        fg=typer.colors.GREEN,
    )
    deepset_service = get_deepset_resource_service(api_key=resolved_api_key)
    deepset_service.setup_multiple_test_resources_sync(
        test_cases=test_cfgs, workspace=resolved_workspace, concurrency=concurrency
    )

    typer.secho("✔ All test-cases attempted.", fg=typer.colors.GREEN)


@tests_app.command("teardown")
def delete_case(
    test_name: str = typer.Argument(..., help="Test-case name (without .yml)."),
    workspace_name: str | None = get_standard_workspace_option(),
    api_key: str | None = get_standard_api_key_option(),
    env_file: str | None = get_standard_env_file_option(),
    test_dir: str | None = typer.Option(
        None,
        help="Directory where test-case YAMLs are stored.",
    ),
) -> None:
    """Teardown a single test-case by name and delete its pipeline + index (if any) from deepset."""
    resolved_api_key, resolved_workspace = setup_deepset_environment(
        api_key=api_key, workspace=workspace_name, env_file=env_file
    )

    if resolved_workspace is None:
        show_cli_error(
            "You need to provide either 'workspace_name' or set the 'DEEPSET_WORKSPACE' environment variable."
        )
        raise typer.Exit(code=1)

    if resolved_api_key is None:
        show_cli_error("You need to provide either 'api_key' or set the 'DEEPSET_API_KEY' environment variable.'")
        raise typer.Exit(code=1)

    repository = FileSystemBenchmarkRepository()
    test_cfg = repository.load_test_case_by_name(name=test_name, task_dir=test_dir)

    typer.secho(f"→ Deleting resources for '{test_name}' from '{resolved_workspace}'…", fg=typer.colors.GREEN)
    deepset_service = get_deepset_resource_service(api_key=resolved_api_key)
    deepset_service.cleanup_test_resources_sync(test_cfg, resolved_workspace)

    typer.secho(f"✔ '{test_name}' resources deleted.", fg=typer.colors.GREEN)


@tests_app.command("teardown-all")
def delete_all(
    workspace_name: str = get_standard_workspace_option(),
    api_key: str | None = get_standard_api_key_option(),
    env_file: str | None = get_standard_env_file_option(),
    concurrency: int = get_standard_concurrency_option(),
    test_dir: str | None = typer.Option(
        None,
        help="Directory where test-case YAMLs are stored.",
    ),
) -> None:
    """Teardown every test-case under `task_dir` and delete pipelines and indexes from deepset."""
    resolved_api_key, resolved_workspace = setup_deepset_environment(
        api_key=api_key, workspace=workspace_name, env_file=env_file
    )

    if resolved_workspace is None:
        show_cli_error(
            "You need to provide either 'workspace_name' or set the 'DEEPSET_WORKSPACE' environment variable."
        )
        raise typer.Exit(code=1)

    if resolved_api_key is None:
        show_cli_error("You need to provide either 'api_key' or set the 'DEEPSET_API_KEY' environment variable.'")
        raise typer.Exit(code=1)

    repository = FileSystemBenchmarkRepository()
    paths = repository.find_all_test_case_paths(test_dir)
    if not paths:
        typer.secho(f"No test-case files found in {test_dir}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # 1) Load all configs
    test_cfgs: list[TestCaseConfig] = []
    for p in paths:
        try:
            cfg = repository.load_test_case_from_path(path=p)
            test_cfgs.append(cfg)
        except Exception as e:
            typer.secho(f"Skipping '{p.stem}' (load error: {e})", fg=typer.colors.YELLOW)

    if not test_cfgs:
        typer.secho("No valid test-case configs to delete.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.secho(
        f"→ Deleting {len(test_cfgs)} test-cases from '{resolved_workspace}' (concurrency={concurrency})…",
        fg=typer.colors.GREEN,
    )
    cli_service = get_deepset_resource_service(api_key=resolved_api_key)
    cli_service.cleanup_multiple_test_resources_sync(
        test_cases=test_cfgs, workspace=resolved_workspace, concurrency=concurrency
    )

    typer.secho("✔ All test-cases teardown attempted.", fg=typer.colors.GREEN)


def create_tests_app() -> typer.Typer:
    """Create the tests CLI app."""
    return tests_app
