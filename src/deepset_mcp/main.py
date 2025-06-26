import argparse
import logging
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.tool_factory import WorkspaceMode, register_all_tools
from deepset_mcp.tools.doc_search import (
    get_docs_config,
    search_docs as search_docs_tool,
)

# Initialize MCP Server
mcp = FastMCP("Deepset Cloud MCP", settings={"log_level": "ERROR"})

logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("fastapi").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("mcp").setLevel(logging.WARNING)


@mcp.prompt()
async def deepset_copilot() -> str:
    """System prompt for the deepset copilot."""
    prompt_path = Path(__file__).parent / "prompts/deepset_copilot_prompt.md"

    return prompt_path.read_text()


# Check if docs search should be enabled
docs_config = get_docs_config()
if docs_config:
    docs_workspace, docs_pipeline_name, docs_api_key = docs_config

    async def search_docs(query: str) -> str:
        """Search the deepset platform documentation.

        This tool allows you to search through deepset's official documentation to find
        information about features, API usage, best practices, and troubleshooting guides.
        Use this when you need to look up specific deepset functionality or help users
        understand how to use deepset features.

        :param query: The search query to execute against the documentation.
        :returns: The formatted search results from the documentation.
        """
        async with AsyncDeepsetClient(api_key=docs_api_key) as client:
            response = await search_docs_tool(
                client=client,
                workspace=docs_workspace,
                pipeline_name=docs_pipeline_name,
                query=query,
            )
        return response

    # Add the tool to the server
    mcp.add_tool(search_docs)

else:
    logging.warning(
        "Documentation search tool not enabled. To enable, set the following environment variables: "
        "DEEPSET_DOCS_WORKSPACE, DEEPSET_DOCS_PIPELINE_NAME, DEEPSET_DOCS_API_KEY"
    )


def main() -> None:
    """Entrypoint for the deepset MCP server."""
    parser = argparse.ArgumentParser(description="Run the Deepset MCP server.")
    parser.add_argument(
        "--workspace",
        "-w",
        help="Deepset workspace (env DEEPSET_WORKSPACE)",
    )
    parser.add_argument(
        "--api-key",
        "-k",
        help="Deepset API key (env DEEPSET_API_KEY)",
    )
    parser.add_argument(
        "--docs-workspace",
        help="Deepset docs search workspace (env DEEPSET_DOCS_WORKSPACE)",
    )
    parser.add_argument(
        "--docs-pipeline-name",
        help="Deepset docs pipeline name (env DEEPSET_DOCS_PIPELINE_NAME)",
    )
    parser.add_argument(
        "--docs-api-key",
        help="Deepset docs pipeline API key (env DEEPSET_DOCS_API_KEY)",
    )
    parser.add_argument(
        "--workspace-mode",
        choices=["implicit", "explicit"],
        default="implicit",
        help="Whether workspace is implicit (from env) or explicit (as parameter). Default: implicit",
    )
    args = parser.parse_args()

    # prefer flags, fallback to env
    workspace = args.workspace or os.getenv("DEEPSET_WORKSPACE")
    api_key = args.api_key or os.getenv("DEEPSET_API_KEY")
    docs_workspace = args.docs_workspace or os.getenv("DEEPSET_DOCS_WORKSPACE")
    docs_pipeline_name = args.docs_pipeline_name or os.getenv("DEEPSET_DOCS_PIPELINE_NAME")
    docs_api_key = args.docs_api_key or os.getenv("DEEPSET_DOCS_API_KEY")

    # Create server configuration
    workspace_mode = WorkspaceMode(args.workspace_mode)

    # Only require workspace for implicit mode
    if workspace_mode == WorkspaceMode.IMPLICIT:
        if not workspace:
            parser.error("Missing workspace: set --workspace or DEEPSET_WORKSPACE (required for implicit mode)")

    if not api_key:
        parser.error("Missing API key: set --api-key or DEEPSET_API_KEY")

    # make sure downstream tools see them (for implicit mode)
    if workspace:
        os.environ["DEEPSET_WORKSPACE"] = workspace
    os.environ["DEEPSET_API_KEY"] = api_key

    # Set docs environment variables if provided
    if docs_workspace:
        os.environ["DEEPSET_DOCS_WORKSPACE"] = docs_workspace
    if docs_pipeline_name:
        os.environ["DEEPSET_DOCS_PIPELINE_NAME"] = docs_pipeline_name
    if docs_api_key:
        os.environ["DEEPSET_DOCS_API_KEY"] = docs_api_key

    # Register all tools based on configuration
    register_all_tools(mcp, workspace_mode, workspace)

    # run with SSE transport (HTTP+Server-Sent Events)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
