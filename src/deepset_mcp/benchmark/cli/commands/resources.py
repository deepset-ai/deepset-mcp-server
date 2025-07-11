from pathlib import Path
from typing import Literal

import typer

from deepset_mcp.benchmark.cli.utils import (
    get_standard_api_key_option,
    get_standard_env_file_option,
    get_standard_workspace_option,
    setup_deepset_environment,
    show_cli_error,
)
from deepset_mcp.benchmark.core.services import get_deepset_resource_service


def create_resource_app(
    resource_type: Literal["pipeline", "index"], resource_name_plural: Literal["pipelines", "indexes"]
) -> typer.Typer:
    """Create a Typer app for managing resources (pipelines or indexes)."""
    app = typer.Typer(help=f"Commands for creating and deleting {resource_name_plural}.")

    @app.command("create")
    def create_resource(
        yaml_path: str | None = typer.Option(None, "--path", "-p", help=f"Path to a {resource_type} YAML file."),
        yaml_content: str | None = typer.Option(
            None,
            "--content",
            "-c",
            help=f"Raw YAML content for the {resource_type}.",
        ),
        resource_name: str = typer.Option(..., "--name", "-n", help=f"Name to assign to the new {resource_type}."),
        workspace_name: str = get_standard_workspace_option(),
        api_key: str | None = get_standard_api_key_option(),
        env_file: str | None = get_standard_env_file_option(),
    ) -> None:
        """Create a single resource from a yaml configuration."""
        if (yaml_path and yaml_content) or (not yaml_path and not yaml_content):
            typer.secho("Error: exactly one of `--path` or `--content` must be provided.", fg=typer.colors.RED)
            raise typer.Exit(code=1)

        if yaml_path:
            resource_yaml = Path(yaml_path).read_text()
        else:
            resource_yaml = yaml_content or ""

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

        deepset_service = get_deepset_resource_service(api_key=resolved_api_key)

        # Call the appropriate service method based on resource type
        if resource_type == "pipeline":
            deepset_service.create_pipeline(workspace=resolved_workspace, name=resource_name, yaml_config=resource_yaml)
        elif resource_type == "index":
            deepset_service.create_index(workspace=resolved_workspace, name=resource_name, yaml_config=resource_yaml)
        else:
            raise ValueError(f"Unknown resource type: {resource_type}")

        typer.secho(
            f"✔ {resource_type.title()} '{resource_name}' created in '{workspace_name}'.", fg=typer.colors.GREEN
        )

    @app.command("delete")
    def delete_resource(
        resource_name: str = typer.Option(..., "--name", "-n", help=f"Name of the {resource_type} to delete."),
        workspace_name: str = get_standard_workspace_option(),
        api_key: str | None = get_standard_api_key_option(),
        env_file: str | None = get_standard_env_file_option(),
    ) -> None:
        """Delete a single resource by name."""
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

        deepset_service = get_deepset_resource_service(api_key=resolved_api_key)

        # Call the appropriate service method based on resource type
        if resource_type == "pipeline":
            deepset_service.delete_pipeline(workspace=resolved_workspace, name=resource_name)
        elif resource_type == "index":
            deepset_service.delete_index(workspace=resolved_workspace, name=resource_name)
        else:
            raise ValueError(f"Unknown resource type: {resource_type}")

        typer.secho(
            f"✔ {resource_type.title()} '{resource_name}' deleted from '{workspace_name}'.", fg=typer.colors.GREEN
        )

    return app


def create_pipeline_app() -> typer.Typer:
    """Create the pipeline CLI app."""
    return create_resource_app("pipeline", "pipelines")


def create_index_app() -> typer.Typer:
    """Create the index CLI app."""
    return create_resource_app("index", "indexes")
