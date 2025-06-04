import typer

from deepset_mcp.benchmark.runner.cli_agent import create_agents_app
from deepset_mcp.benchmark.runner.cli_index import create_index_app
from deepset_mcp.benchmark.runner.cli_pipeline import create_pipeline_app
from deepset_mcp.benchmark.runner.cli_tests import create_tests_app

app = typer.Typer(
    name="deepset",
    help="Deepset Copilot CLI for managing pipelines and running benchmarks.",
    no_args_is_help=True,
)

app.add_typer(
    create_agents_app(),
    name="agent",
    help="Run agents against test cases.",
    no_args_is_help=True,
)

app.add_typer(create_tests_app(), name="test", help="Setup test cases on deepset.")

app.add_typer(
    create_pipeline_app(),
    name="pipeline",
    help="Manage pipelines on deepset.",
    no_args_is_help=True,
)

app.add_typer(
    create_index_app(),
    name="index",
    help="Manage indexes on deepset.",
    no_args_is_help=True,
)


if __name__ == "__main__":
    app()
