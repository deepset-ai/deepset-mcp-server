import typer

from deepset_mcp.benchmark.runner.setup_actions import setup_index
from deepset_mcp.benchmark.runner.teardown_actions import teardown_index

index_app = typer.Typer(help="Commands for creating and deleting indexes.")


@index_app.command("create")
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
    """Create a single index from a yaml configuration."""
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


@index_app.command("delete")
def delete_index(
    index_name: str = typer.Option(..., "--name", "-n", help="Name of the index to delete."),
    workspace_name: str = typer.Option(
        "default", "--workspace", "-w", help="Workspace from which to delete the index."
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="Explicit DP_API_KEY to use (overrides environment).",
    ),
) -> None:
    """Delete a single index by name."""
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


def create_index_app() -> typer.Typer:
    """Create the index CLI app."""
    return index_app
