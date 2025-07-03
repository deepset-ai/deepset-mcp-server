import argparse
import logging
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from deepset_mcp.tool_factory import WorkspaceMode, register_tools

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


@mcp.prompt()
async def deepset_recommended_prompt() -> str:
    """Recommended system prompt for the deepset copilot."""
    prompt_path = Path(__file__).parent / "prompts/deepset_debugging_agent.md"

    return prompt_path.read_text()


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
    parser.add_argument(
        "--tools",
        nargs="*",
        help="Space-separated list of tools to register (default: all)",
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="List all available tools and exit",
    )
    args = parser.parse_args()

    # Handle --list-tools flag early
    if args.list_tools:
        from deepset_mcp.tool_factory import TOOL_REGISTRY

        print("Available tools:")
        for tool_name in sorted(TOOL_REGISTRY.keys()):
            print(f"  {tool_name}")
        return

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

    # Parse tool names if provided
    tool_names = None
    if args.tools:
        tool_names = set(args.tools)

    # Register tools based on configuration
    register_tools(mcp, workspace_mode, workspace, tool_names)

    # run with SSE transport (HTTP+Server-Sent Events)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
