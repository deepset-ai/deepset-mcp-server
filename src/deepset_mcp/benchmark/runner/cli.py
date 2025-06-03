import typer

from deepset_mcp.benchmark.runner.config_loader import (
    find_all_test_case_paths,
    load_test_case_by_name,
    load_test_case_from_path,
)
from deepset_mcp.benchmark.runner.models import TestCaseConfig
from deepset_mcp.benchmark.runner.setup_actions import (
    setup_all,
    setup_index,
    setup_pipeline,
    setup_test_case,
)
from deepset_mcp.benchmark.runner.teardown_actions import (
    teardown_all,
    teardown_index,
    teardown_pipeline,
    teardown_test_case,
)

app = typer.Typer(help="Short commands for listing/creating test cases, pipelines, and indexes.")


@app.command("list-cases")
def list_cases(
    task_dir: str | None = typer.Option(
        None,
        help="Directory where all test-case YAMLs live (`benchmark/tasks/*.yml`).",
    ),
) -> None:
    """List all test-case files (base names) under `task_dir`."""
    paths = find_all_test_case_paths(task_dir)
    if not paths:
        typer.secho(f"No test-case files found in {task_dir}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    for p in paths:
        typer.echo(f" • {p.stem}")


@app.command("create-case")
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
    task_dir: str | None = typer.Option(
        None,
        help="Directory where test-case YAMLs are stored.",
    ),
) -> None:
    """Load a single test-case by name and create its pipeline + index (if any) in `workspace_name`."""
    try:
        test_cfg = load_test_case_by_name(name=test_name, task_dir=task_dir)
    except FileNotFoundError:
        typer.secho(f"Test-case '{test_name}' not found under {task_dir}.", fg=typer.colors.RED)
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


@app.command("create-all")
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
    task_dir: str | None = typer.Option(
        None,
        help="Directory where test-case YAMLs are stored.",
    ),
) -> None:
    """Load every test-case under `task_dir` and create pipelines + indexes in `workspace_name` in parallel."""
    paths = find_all_test_case_paths(task_dir)
    if not paths:
        typer.secho(f"No test-case files found in {task_dir}", fg=typer.colors.RED)
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


@app.command("create-pipe")
def create_pipe(
    yaml_path: str | None = typer.Option(None, "--path", "-p", help="Path to a pipeline YAML file."),
    yaml_content: str | None = typer.Option(
        None, "--content", "-c", help="Raw YAML string for the pipeline (instead of a file)."
    ),
    pipeline_name: str = typer.Option(..., "--name", "-n", help="Name to assign to the new pipeline."),
    workspace_name: str = typer.Option(
        "default", "--workspace", "-w", help="Workspace in which to create the pipeline."
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="Explicit DP_API_KEY to use (overrides environment).",
    ),
) -> None:
    """Create a single pipeline in `workspace_name`."""
    if (yaml_path and yaml_content) or (not yaml_path and not yaml_content):
        typer.secho("Error: exactly one of `--path` or `--content` must be provided.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    try:
        setup_pipeline(
            yaml_path=yaml_path,
            yaml_content=yaml_content,
            pipeline_name=pipeline_name,
            workspace_name=workspace_name,
            api_key=api_key,
        )
        typer.secho(f"✔ Pipeline '{pipeline_name}' created in '{workspace_name}'.", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"✘ Failed to create pipeline '{pipeline_name}': {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command("create-index")
def create_index(
    yaml_path: str | None = typer.Option(None, "--path", "-p", help="Path to an index YAML file."),
    yaml_content: str | None = typer.Option(None, "--content", "-c", help="Raw YAML string for the index."),
    index_name: str = typer.Option(..., "--name", "-n", help="Name to assign to the new index."),
    workspace_name: str = typer.Option("default", "--workspace", "-w", help="Workspace in which to create the index."),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="Explicit DP_API_KEY to use (overrides environment).",
    ),
    description: str | None = typer.Option(None, "--desc", help="Optional description for the index."),
) -> None:
    """Create a single index in `workspace_name`."""
    if (yaml_path and yaml_content) or (not yaml_path and not yaml_content):
        typer.secho("Error: exactly one of `--path` or `--content` must be provided.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    try:
        setup_index(
            yaml_path=yaml_path,
            yaml_content=yaml_content,
            index_name=index_name,
            workspace_name=workspace_name,
            api_key=api_key,
            description=description,
        )
        typer.secho(f"✔ Index '{index_name}' created in '{workspace_name}'.", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"✘ Failed to create index '{index_name}': {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command("delete-case")
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
    task_dir: str | None = typer.Option(
        None,
        help="Directory where test-case YAMLs are stored.",
    ),
) -> None:
    """Load a single test-case by name and delete its pipeline + index (if any) from `workspace_name`."""
    try:
        test_cfg = load_test_case_by_name(name=test_name, task_dir=task_dir)
    except FileNotFoundError:
        typer.secho(f"Test-case '{test_name}' not found under {task_dir}.", fg=typer.colors.RED)
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


@app.command("delete-all")
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
    task_dir: str | None = typer.Option(
        None,
        help="Directory where test-case YAMLs are stored.",
    ),
) -> None:
    """Load every test-case under `task_dir` and delete pipelines + indexes from `workspace_name` in parallel."""
    paths = find_all_test_case_paths(task_dir)
    if not paths:
        typer.secho(f"No test-case files found in {task_dir}", fg=typer.colors.RED)
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


@app.command("delete-pipe")
def delete_pipe(
    pipeline_name: str = typer.Option(..., "--name", "-n", help="Name of the pipeline to delete."),
    workspace_name: str = typer.Option(
        "default", "--workspace", "-w", help="Workspace from which to delete the pipeline."
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="Explicit DP_API_KEY to use (overrides environment).",
    ),
) -> None:
    """Delete a single pipeline from `workspace_name`."""
    try:
        teardown_pipeline(
            pipeline_name=pipeline_name,
            workspace_name=workspace_name,
            api_key=api_key,
        )
        typer.secho(f"✔ Pipeline '{pipeline_name}' deleted from '{workspace_name}'.", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"✘ Failed to delete pipeline '{pipeline_name}': {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command("delete-index")
def delete_index(
    index_name: str = typer.Option(..., "--name", "-n", help="Name of the index to delete."),
    workspace_name: str = typer.Option("default", "--workspace", "-w", help="Workspace from which to delete the index."),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="Explicit DP_API_KEY to use (overrides environment).",
    ),
) -> None:
    """Delete a single index from `workspace_name`."""
    try:
        teardown_index(
            index_name=index_name,
            workspace_name=workspace_name,
            api_key=api_key,
        )
        typer.secho(f"✔ Index '{index_name}' deleted from '{workspace_name}'.", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"✘ Failed to delete index '{index_name}': {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


def cli() -> None:
    """Entrypoint for the benchmark CLI."""
    app()


if __name__ == "__main__":
    cli()
