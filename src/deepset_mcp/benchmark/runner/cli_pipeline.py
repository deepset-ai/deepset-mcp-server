import typer

from deepset_mcp.benchmark.runner.setup_actions import setup_pipeline
from deepset_mcp.benchmark.runner.teardown_actions import teardown_pipeline

pipeline_app = typer.Typer(help="Commands for creating and deleting pipelines.")


@pipeline_app.command("create")
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
    """Create a single pipeline from a yaml configuration."""
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


@pipeline_app.command("delete")
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


def create_pipeline_app() -> typer.Typer:
    """Create the agent benchmark CLI app."""
    return pipeline_app
