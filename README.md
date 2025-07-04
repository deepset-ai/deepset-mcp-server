# MCP Server for the deepset AI platform

The deepset MCP server exposes tools that MCP clients like Claude or Cursor can use to interact with the deepset AI platform.

Agents can use these tools to:

- develop and iterate on Pipelines or Indexes
- debug Pipelines and Indexes
- search the deepset AI platform documentation

## Contents

- [1. Installation](#installation)
  - [1.1. Claude Desktop](#claude-desktop-app)
  - [1.2. Other MCP Clients](#other-mcp-clients)
  - [1.3. Advanced Configuration](#advanced-configuration)
- [2. Prompts](#prompts)
- [3. Use Cases](#use-cases)
  - [3.1. Creating Pipelines](#creating-pipelines)
  - [3.2. Debugging Pipelines](#debugging-pipelines)
- [4. CLI](#cli)





![GIF showing CLI interaction with the MCP server](assets/deepset-mcp-3.gif)


## Installation

### Claude Desktop App

**Prerequisites:**
- [Claude Desktop App](https://claude.ai/download) needs to be installed
- You need to be on the Claude Pro, Team, Max, or Enterprise plan
- You need an installation of [Docker](https://docs.docker.com/desktop/) ([Go here](#using-uv-instead-of-docker) if you want to use `uv` instead of Docker)
- You need an [API key](https://docs.cloud.deepset.ai/docs/generate-api-key) for the deepset platform

**Steps:**
1. Go to: `/Users/your_user/Library/Application Support/Claude` (Mac)
2. Either open or create `claude_desktop_config.json`
3. Add the following json as your config (or update your existing config if you are already using other MCP servers)

```json
{
  "mcpServers": {
    "deepset": {
      "command": "/usr/local/bin/docker",
      "args": [
        "run",
        "-i",
        "-e",
        "DEEPSET_WORKSPACE",
        "-e",
        "DEEPSET_API_KEY",
        "deepset/deepset-mcp-server:main"
      ],
      "env": {
       "DEEPSET_WORKSPACE":"<WORKSPACE>",
       "DEEPSET_API_KEY":"<DEEPSET_API_KEY>"
     }

    }
  }
}
```

4. Quit and start the Claude Desktop App
5. The deepset server should appear in the "Search and Tools" menu (this takes a few seconds as the Docker image needs to be downloaded and started)

![Screenshot of the Search and Tools menu in the Claude Desktop App with deepset server running.](assets/claude_desktop_with_tools.png)



#### Using uv instead of Docker

Running the server with uv gives you faster startup time and consumes slightly less resources on your system.

1. [Install uv](https://docs.astral.sh/uv/guides/install-python/) if you don't have it yet
2. Put the following into your `claude_desktop_config.json`

```python
{
  "mcpServers": {
    "deepset": {
      "command": "uvx",
      "args": [
        "deepset-mcp"
      ],
      "env": {
       "DEEPSET_WORKSPACE":"<WORKSPACE>",
       "DEEPSET_API_KEY":"<DEEPSET_API_KEY>"
     }

    }
  }
}
```

This will load the [deepset-mcp package from PyPi](https://pypi.org/project/deepset-mcp/) and install it into a temporary virtual environment.

3. Quit and start the Claude Desktop App



### Other MCP Clients

`deepset-mcp` can be used with other MCP clients.

Here is where you need to configure `deepset-mcp` for:

- [Cursor](https://docs.cursor.com/context/mcp#using-mcp-json)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/mcp#configure-mcp-servers)
- [Gemini CLI](https://cloud.google.com/gemini/docs/codeassist/use-agentic-chat-pair-programmer#configure-mcp-servers)

Generally speaking, depending on your installation, you need to configure an MCP client with one of the following commands:

`uvx deepset-mcp --workspace your_workspace --api-key your_api_key`

If you installed the deepset-mcp package globally and added it to your `PATH`, you can just run:

`deepset-mcp --workspace your_workspace --api-key your_api_key`

The server runs locally using `stdio` to communicate with the client.

### Advanced Configuration

#### Tool Selection

You can customize which tools the MCP server should expose.
Use the `´--tools`-option in your config to explicitly specify which tools should be exposed.

You can list available tools with: `deepset-mcp --list-tools`.

To only expose the `list_pipelines` and `get_pipeline` tools you would use the following command:

`deepset-mcp --tools list_pipelines get_pipeline`

For smooth operations, you should always expose the `get_from_object_store` and `get_slice_from_object_store` tools.


#### Allowing access to multiple workspaces

The basic configuration uses a hardcoded workspace which you pass in via the `DEEPSET_WORKSPACE` environment variable.
If you want to allow an agent to access resources from multiple workspaces, you can use `--workspace-mode explicit`
in your config.

For example:

```json
{
  "mcpServers": {
    "deepset": {
      "command": "uvx",
      "args": [
        "deepset-mcp",
        "--workspace-mode",
        "explicit"
      ],
      "env": {
       "DEEPSET_API_KEY":"<DEEPSET_API_KEY>"
     }

    }
  }
}
```

An agent using the MCP server now has access to all workspaces that the API-key has access to. When interacting with most
resources, you will need to tell the agent what workspace it should use to perform an action. Instead of prompting it
with "list my pipelines", you would now have to prompt it with "list my pipelines in the staging workspace".


## Prompts

All tools exposed through the MCP server have minimal prompts. Any Agent interacting with these tools benefits from an additional system prompt.

View the **recommended prompt** [here](src/deepset_mcp/prompts/deepset_debugging_agent.md).

This prompt is also exposed as the `deepset_recommended_prompt` on the MCP server.
In Claude Desktop, click `add from deepset` to add the prompt to your context.
A better way to add system prompts in Claude Desktop is through "Projects".

You can customize the system prompt to your specific needs.


## Use Cases

The primary way to use the deepset MCP server is through an LLM that interacts with the deepset MCP tools in an agentic way.

### Creating Pipelines

Tell the LLM about the type of pipeline you want to build. Creating new pipelines will work best if you use terminology
that is similar to what is used on the deepset AI platform or in Haystack.

Your prompts should be precise and specific.

Examples:

- "Build a RAG pipeline with hybrid retrieval that uses claude-sonnet-4 from Anthropic as the LLM."
- "Build an Agent that can iteratively search the web (deep research). Use SerperDev for web search and GPT-4o as the LLM."

You can also instruct the LLM to deploy pipelines, and it can issue search requests against pipelines to test them.

**Best Practices**

- be specific in your requests
- point the LLM to examples, if there is already a similar pipeline in your workspace, then ask it to look at it first, 
if you have a template in mind, ask it to look at the template
- instruct the LLM to iterate with you locally before creating the pipeline, have it validate the drafts and then let it 
create it once the pipeline is up to your standards


### Debugging Pipelines

The `deepset-mcp` tools allow LLMs to debug pipelines on the deepset AI platform.
Primary tools used for debugging are:
- get_logs
- validate_pipeline
- search_pipeline
- search_pipeline_templates
- search_component_definition

You can ask the LLM to check the logs of a specific pipeline in case it is already deployed but has errors.
The LLM will find errors in the logs and devise strategies to fix them.
If your pipeline is not deployed yet, the LLM can autonomously validate it and fix validation errors.

## CLI
You can use the MCP server as a Haystack Agent through a command-line interface.

Install with `uvx tool install "deepset-mcp[cli]"`.

Start the interactive CLI with:

`deepset agent chat`

You can set environment variables before starting the Agent via:

```shell
export DEEPSET_API_KEY=your_key
export DEEPSET_WORKSPACE=your_workspace
```

You can also provide an `.env` file using the `--env-file` option:

`deepset agent chat --env-file your/env/.file`

The agent will load environment variables from the file on startup.
