# MCP Server for the deepset AI platform

This is the _official_ MCP server for the [deepset AI platform](https://www.deepset.ai/products-and-services/deepset-ai-platform).
It allows Agents in tools like Cursor or Claude Code to build and debug pipelines on the deepset platform.

The MCP server exposes up to 30 hand-crafted tools that are optimized for Agents interacting with the deepset platform.
Using the server, you benefit from faster creation of pipelines or indexes and speedy issue resolution through agentic debugging.



## Contents

- [1. Installation](#installation)
  - [1.1 Cursor](#cursor)
  - [1.2 Claude Desktop](#claude-desktop-app)
  - [1.3 Other MCP Clients](#other-mcp-clients)
  - [1.4 Docker](#docker)
- [2. Configuration](#configuration)
  - [2.1 Multiple Workspaces](#multiple-workspaces)
  - [2.2 Manage Tools](#manage-tools)
  - [2.3 Reduce Tool Count](#reduce-tool-count)
  - [2.4 Prompts](#prompts)
- [3. Use Cases](#use-cases)
  - [3.1. Creating Pipelines](#creating-pipelines)
  - [3.2. Debugging Pipelines](#debugging-pipelines)
- [4. Reference](#reference)
  - [4.1 deepset-mcp](#deepset-mcp)
  - [4.2 Tools](#tools)
    - [4.2.1 Pipelines](#pipelines)
    - [4.2.2 Indexes](#indexes)
    - [4.2.3 Templates](#templates)
    - [4.2.4 Workspaces](#workspaces)
    - [4.2.5 Secrets](#secrets)
    - [4.2.6 Object Store](#object-store)
    - [4.2.7 Components](#components)
    - [4.2.8 Documentation](#documentation)
- [5. Known Limitations](#known-limitations)


## Installation

Before configuring MCP clients to work with `deepset-mcp`, you need to install [uv](https://docs.astral.sh/uv/), a modern Python package manager.

If `uv` is not installed on your system, you can install it via:

`pipx install uv` (if Python is installed on your system)

or

_Mac/Linux_

`curl -LsSf https://astral.sh/uv/install.sh | sh` (if you do not want to manage a Python installation yourself)

_Windows_

`powershell -c "irm https://astral.sh/uv/install.ps1 | more"`

Once you have `uv` installed, you can follow one of the guides below to configure `deepset-mcp` with your MCP client of choice.

### Cursor

**Prerequisites**
- Cursor needs to be installed
- You need an account with Cursor
- You need to [create an API key](https://docs.cloud.deepset.ai/docs/generate-api-key) for the deepset platform
- `uv` needs to be installed ([see above](#installation))

**Configuration**

Latest instructions on how to set up an MCP server for Cursor are covered in their [documentation](https://docs.cursor.com/context/mcp#using-mcp-json).
You can either configure the MCP server for a single Cursor project or globally across all projects.

To configure the `deepset-mcp` server for a single project:

1. create a file with the name `mcp.json` in your `.cursor` directory at the root of the project
2. Add the following configuration

```json
{
  "mcpServers": {
    "deepset": {
      "command": "uvx",
      "args": ["deepset-mcp"],
      "env": {
        "DEEPSET_WORKSPACE": "the deepset workspace that you want to use",
        "DEEPSET_API_KEY": "your deepset API key"
      }
    }
  }
}
```

This creates a virtual environment for the `deepset-mcp` package and runs the command to start the server.
The `deepset-mcp` server should appear in the "Tools & Integrations" section of your "Cursor Settings".
The tools on the server are now available to the Cursor Agent.

It is recommended to create a file named `.cursorrules` at the root of your project (if not already there)
and to add the [recommended prompt](#prompts) to the file.
This ensures optimal integration between the Cursor Agent and the deepset-mcp tools.


### Claude Desktop App

**Prerequisites**
- [Claude Desktop App](https://claude.ai/download) needs to be installed
- You need to be on the Claude Pro, Team, Max, or Enterprise plan
- You need to [create an API key](https://docs.cloud.deepset.ai/docs/generate-api-key) for the deepset platform
- `uv` needs to be installed ([see above](#installation))

**Configuration**

Latest instructions on how to configure Claude Desktop with MCP can be found in [Anthropic's MCP documentation](https://modelcontextprotocol.io/quickstart/user).
To configure Claude Desktop with the `deepset-mcp`-package, follow these steps:


1. Go to: `/Users/your_user/Library/Application Support/Claude` (Mac)
2. Either open or create `claude_desktop_config.json`
3. Add the following json as your config (or update your existing config if you are already using other MCP servers)

```json
{
  "mcpServers": {
    "deepset": {
      "command": "uvx",
      "args": ["deepset-mcp"],
      "env": {
        "DEEPSET_WORKSPACE": "the deepset workspace that you want to use",
        "DEEPSET_API_KEY": "your deepset API key"
      }
    }
  }
}
```
4. Quit and start the Claude Desktop App
5. The deepset server should appear in the "Search and Tools" menu (it might take a few seconds to start the server)

For best integration with Claude Desktop, it is recommended to create a Claude Desktop "Project" and to add the
[recommended prompt](#prompts) as the "project instructions".


### Other MCP Clients

`deepset-mcp` can be used with other MCP clients.

Here is where you need to configure `deepset-mcp` for:

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/mcp#configure-mcp-servers)
- [Gemini CLI](https://cloud.google.com/gemini/docs/codeassist/use-agentic-chat-pair-programmer#configure-mcp-servers)

Depending on your installation, you need to configure an MCP client with one of the following commands:

`uvx deepset-mcp --workspace your_workspace --api-key your_api_key`

If you installed the deepset-mcp package globally and added it to your `PATH`, you can just run:

`deepset-mcp --workspace your_workspace --api-key your_api_key`

The server runs locally using `stdio` to communicate with the client.

### Docker

In case you prefer to isolate the `deepset-mcp` server in a Docker container, you can use our [official Docker image](https://hub.docker.com/r/deepset/deepset-mcp-server) to run the server.

If running with Docker, you need to use the following configuration with your MCP Client:

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


## Configuration

### Multiple Workspaces

In the default configuration, the Agent can only interact with resources in a fixed deepset workspace.
You configure this deepset workspace either through the `DEEPSET_WORKSPACE` environment variable
or the `--workspace` option.

The `--workspace-mode`-option (default: `static`) determines if the Agent can interact with a fixed, pre-configured workspace,
or if it should have access to resources in multiple workspaces.
If you want to allow an Agent to access resources from multiple workspaces, use `--workspace-mode dynamic`
in your configuration.

For example:

```json
{
  "mcpServers": {
    "deepset": {
      "command": "uvx",
      "args": [
        "deepset-mcp",
        "--workspace-mode",
        "dynamic"
      ],
      "env": {
       "DEEPSET_API_KEY":"<DEEPSET_API_KEY>"
     }

    }
  }
}
```

An Agent using the MCP server can now access all workspaces that the API-key has access to. When interacting with most
resources, you need to tell the agent what workspace it should use to perform an action. Instead of prompting it
with "list my pipelines", you now have to prompt it with "list my pipelines in the staging workspace".


### Manage Tools

Not all tools are needed for all tasks. You can toggle available tools in most MCP clients (e.g. [Cursor](https://docs.cursor.com/context/mcp#toggling-tools)).
If your MCP client does not support toggling tools, you can select which tools should be available by using the `--tools`-option.

Run `uvx deepset-mcp --list-tools` in your terminal to get a list of all available tools.

Then update your MCP configuration with the tools that you want to use with your MCP client.

Here is an exemplary Cursor `mcp.json` with tool selection:

```json
{
  "mcpServers": {
    "deepset-mcp": {
      "command": "uvx",
      "args": [
        "deepset-mcp",
        "--tools",
        "create_pipeline",
        "get_from_object_store",
        "get_slice_from_object_store",
        "list_pipelines",
        "search_templates"
      ],
      "env": {
        "DEEPSET_WORKSPACE": "",
        "DEEPSET_API_KEY": ""
      }
    }
  }
}
```

The MCP server now only exposes the five tools specifically added in the configuration file instead of exposing all tools.


### Reduce Tool Count

You can view documentation for all tools in the [tools section](#tools). For many workflows, you will not need all tools.
In this case, it is recommended to deactivate tools that are not needed. Using fewer tools has the following benefits:

- some MCP clients limit the maximum number of tools
- the Agent will be more focused on the task at hand and not call tools that it does not need
- some savings for input tokens (minimal)

If you are working in `static` workspace mode, you can deactivate the following tools:
- `list_workspaces`
- `get_workspace`
- `create_workspace`

In `dynamic` workspace mode, activate the `list_workspaces` but not the `get_workspace` tool.
You only need to activate the `create_workspace`-tool if you want your Agent to create workspaces.

If you are not working with custom components, you can deactivate the following tools:
- `get_custom_components`
- `get_latest_custom_component_installation_logs`
- `list_custom_component_installations`

For components and templates, the `search` and `get` tools are often sufficient and the Agent does not need access to a dedicated `list` tool.
For that reason, if you need to lower the tool count, you can deactivate the following tools:
- `list_component_families`
- `list_templates`

`list_secrets` and `get_secret` return the same depth of information for each respective secret.
Therefore, you can deactivate the `get_secret`-tool.

If you need to reduce the tool count further, review your objectives and select the tools that the Agent will need to complete your planned tasks.

If your pipelines do not require an index, you can deactivate all [index tools](#indexes).
If you are only working with a single index that is already created and deployed, and you intend to create or debug connected pipelines, you could deactivate
all index tools except `get_index` because the Agent does not need to interact with the index beyond reading its configuration.

If you are only working on indexes but not pipelines, you might deactivate all [pipeline tools](#pipelines).


**Tools You Should Keep**


You should **not** deactivate any tools related to the [object store](#object-store). These tools are special tools that help
with lowering input token count for Agents and speeding up execution by allowing to call tools with outputs from other tools.

The [documentation tool](#documentation) and the [template tools](#templates) are important for most tasks. The Agent
frequently uses templates as examples for pipeline creation or debugging. The documentation helps the Agent to understand
the fundamentals of the platform.


### Prompts

All tools exposed through the MCP server have minimal prompts. Any Agent interacting with these tools benefits from an additional system prompt.

View the **recommended prompt** [here](src/deepset_mcp/prompts/deepset_debugging_agent.md).

This prompt is also exposed as the `deepset_recommended_prompt` on the MCP server.

In Cursor, add the prompt to `.cursorrules`.

In Claude Desktop, create a "Project" and add the prompt as system instructions.

You may find that customizing the prompt for your specific needs yields best results.


## Use Cases

The primary way to use the deepset MCP server is through an LLM that interacts with the deepset MCP tools in an agentic way.

### Creating Pipelines

Tell the Agent about the type of pipeline you want to build. Creating new pipelines will work best if you use terminology
that is similar to what is used on the deepset AI platform or in Haystack.

Your prompts should be precise and specific.

Examples:

- "Build a RAG pipeline with hybrid retrieval that uses claude-sonnet-4 from Anthropic as the LLM."
- "Build an Agent that can iteratively search the web (deep research). Use SerperDev for web search and GPT-4o as the LLM."

You can also instruct the Agent to deploy pipelines, and it can issue search requests against pipelines to test them.

**Best Practices**

- be specific in your requests
- point the Agent to examples, if there is already a similar pipeline in your workspace, then ask it to look at it first, 
if you have a template in mind, ask it to look at the template
- instruct the Agent to iterate with you locally before creating the pipeline, have it validate the drafts and then let it 
create it once the pipeline is up to your standards


### Debugging Pipelines

The `deepset-mcp` tools allow Agents to debug pipelines on the deepset AI platform.
Primary tools used for debugging are:
- get_logs
- validate_pipeline
- search_pipeline
- search_pipeline_templates
- search_component_definition

You can ask the Agent to check the logs of a specific pipeline in case it is already deployed but has errors.
The Agent will find errors in the logs and devise strategies to fix them.
If your pipeline is not deployed yet, the Agent can autonomously validate it and fix validation errors.

## Reference

### deepset-mcp

The `deepset-mcp`-command starts the `deepset-mcp` server.

You can run it in your terminal via `uvx deepset-mcp`.

If you want to run a specific version, you can run:

`uvx --from "deepset-mcp==0.0.3" deepset-mcp`

The following options are available:

| Option           | Shorthand | Description                                                                                                                                                                                                |
|------------------|-----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| --api-key        | -k        | The deepset API key to use. Can also be set it via the "DEEPSET_API_KEY" environment variable.                                                                                                             |
| --workspace      | -w        | The deepset workspace to use. Can also be set via the "DEEPSET_WORKSPACE" environment variable.                                                                                                            |
| --workspace-mode | -m        | If you want to allow an Agent to access multiple workspaces (Options: static, dynamic; default: static)                                                                                                    |
| --list-tools     | -l        | List all available tools (does not start the server).                                                                                                                                                      |
| --tools          | -t        | Pass a space separated list of tool names that you want the server to register.                                                                                                                            |
| --docs-share-url | -d        | Pass a [shared prototype](https://docs.cloud.deepset.ai/docs/share-a-pipeline-prototype) URL to customize which pipeline the Agent uses for documentation search (default: official deepset documentation) |


### Tools

The deepset-mcp package exposes a set of tools to interact with the deepset platform. Tools can be activated or deactivated
in most MCP clients. Users can also use the `--tools` option to configure which tools should be provided by the MCP server.

#### Pipelines

**List Pipelines**

| Parameter          | Type | Description                                                                                                    |
|--------------------|------|----------------------------------------------------------------------------------------------------------------|
| workspace          | str  | The name of the workspace that the pipelines should be listed from (only exposed in `dynamic` workspace mode). |
 

The `list_pipelines`-tool returns a list of all pipelines in a workspace. The pipelines are returned in a condensed version without their full yaml configuration.

**Get Pipeline**

| Parameter          | Type | Description                                                                                    |
|--------------------|------|------------------------------------------------------------------------------------------------|
| pipeline_name      | str  | The name of the pipeline to get.                                                               |
| workspace          | str  | The name of the workspace to get the pipeline from (only exposed in `dynamic` workspace mode). |
 

The `get_pipeline`-tool returns the full pipeline object including its yaml configuration.

**Create Pipeline**

| Parameter          | Type | Description                                                                                                  |
|--------------------|------|--------------------------------------------------------------------------------------------------------------|
| pipeline_name      | str  | The name to use for the new pipeline.                                                                        |
| yaml_configuration | str  | The yaml configuration defining the pipeline.                                                                |
| workspace          | str  | The name of the workspace that the pipeline should be created in (only exposed in `dynamic` workspace mode). |
 

The `create_pipeline`-tool returns a success message and the full pipeline object if pipeline creation was successful.
If there are validation errors during creation, the errors are returned alongside the pipeline object.

**Update Pipeline**

| Parameter                  | Type | Description                                                                                                  |
|----------------------------|------|--------------------------------------------------------------------------------------------------------------|
| pipeline_name              | str  | The name of the pipeline to update.                                                                          |
| original_config_snippet    | str  | A snippet from the current yaml configuration that should be replaced.                                       |
| replacement_config_snippet | str  | A snippet of yaml configuration that the original snippet should be replaced with.                           |
| workspace                  | str  | The name of the workspace that the pipeline should be updated in (only exposed in `dynamic` workspace mode). |
 

The `update_pipeline`-tool returns a success message and the full pipeline object if the pipeline update was successful.
If there are validation errors during the update, the errors are returned alongside the pipeline object.

**Validate Pipeline**

| Parameter          | Type | Description                                                                                                    |
|--------------------|------|----------------------------------------------------------------------------------------------------------------|
| yaml_configuration | str  | The yaml configuration to validate.                                                                            |
| workspace          | str  | The name of the workspace to validate the pipeline against (only exposed in `dynamic` workspace mode).        |
 

The `validate_pipeline`-tool validates a pipeline configuration without creating it. Returns validation results including any errors or warnings found in the configuration.

**Get Pipeline Logs**

| Parameter          | Type | Description                                                                                                    |
|--------------------|------|----------------------------------------------------------------------------------------------------------------|
| pipeline_name      | str  | The name of the pipeline to get logs for.                                                                      |
| limit              | int  | The maximum number of log entries to return (default: 30).                                                     |
| level              | str  | The log level to filter by. Options: `info`, `warning`, `error`.                                               |
| workspace          | str  | The name of the workspace to get pipeline logs from (only exposed in `dynamic` workspace mode).               |
 

The `get_pipeline_logs`-tool returns log entries for a specific pipeline. Logs are returned in chronological order with the most recent entries first.

**Deploy Pipeline**

| Parameter          | Type | Description                                                                                                    |
|--------------------|------|----------------------------------------------------------------------------------------------------------------|
| pipeline_name      | str  | The name of the pipeline to deploy.                                                                            |
| workspace          | str  | The name of the workspace to deploy the pipeline from (only exposed in `dynamic` workspace mode).             |
 

The `deploy_pipeline`-tool deploys a pipeline to make it active and available for execution.
Deployment takes up to 5 minutes. The tool will wait for the deployment before returning.
It returns a success message when the deployment was successful.

**Search Pipeline**

| Parameter          | Type | Description                                                                                                    |
|--------------------|------|----------------------------------------------------------------------------------------------------------------|
| pipeline_name      | str  | The name of the pipeline to use for searching.                                                                 |
| query              | str  | The search query to execute using the pipeline.                                                                |
| workspace          | str  | The name of the workspace containing the pipeline (only exposed in `dynamic` workspace mode).                 |
 

The `search_pipeline`-tool executes a search query using the specified pipeline. Returns search results based on the pipeline's configured search logic and data sources.

#### Indexes

**List Indexes**

| Parameter          | Type | Description                                                                                                    |
|--------------------|------|----------------------------------------------------------------------------------------------------------------|
| workspace          | str  | The name of the workspace that the indexes should be listed from (only exposed in `dynamic` workspace mode).  |

The `list_indexes`-tool returns a list of all indexes in a workspace. The indexes are returned in a condensed version without their full yaml configuration.

**Get Index**

| Parameter          | Type | Description                                                                                    |
|--------------------|------|------------------------------------------------------------------------------------------------|
| index_name         | str  | The name of the index to get.                                                                  |
| workspace          | str  | The name of the workspace to get the index from (only exposed in `dynamic` workspace mode).   |

The `get_index`-tool returns the full index object including its yaml configuration.

**Create Index**

| Parameter          | Type | Description                                                                                                  |
|--------------------|------|--------------------------------------------------------------------------------------------------------------|
| index_name         | str  | The name to use for the new index.                                                                           |
| yaml_configuration | str  | The yaml configuration defining the index.                                                                   |
| description        | str  | A description of the index purpose and contents.                                                             |
| workspace          | str  | The name of the workspace that the index should be created in (only exposed in `dynamic` workspace mode).   |

The `create_index`-tool returns a success message and the full index object if index creation was successful.
If there are validation errors during creation, the errors are returned alongside the index object.

**Update Index**

| Parameter              | Type | Description                                                                                                  |
|------------------------|------|--------------------------------------------------------------------------------------------------------------|
| workspace              | str  | The name of the workspace that the index should be updated in (only exposed in `dynamic` workspace mode).   |
| index_name             | str  | The name of the index to update.                                                                             |
| updated_index_name     | str  | The new name for the index (optional).                                                                       |
| yaml_configuration     | str  | The updated yaml configuration for the index (optional).                                                     |

The `update_index`-tool returns a success message and the full index object if the index update was successful.
If there are validation errors during the update, the errors are returned alongside the index object.

**Deploy Index**

| Parameter          | Type | Description                                                                                                    |
|--------------------|------|----------------------------------------------------------------------------------------------------------------|
| workspace          | str  | The name of the workspace to deploy the index from (only exposed in `dynamic` workspace mode).               |
| index_name         | str  | The name of the index to deploy.                                                                              |

The `deploy_index`-tool deploys an index to make it active and available for use.
It returns a success message when the deployment was successful or validation errors if there are issues.


#### Templates

**List Templates**

| Parameter          | Type | Description                                                                                                    |
|--------------------|------|----------------------------------------------------------------------------------------------------------------|
| workspace          | str  | The name of the workspace that the templates should be listed from (only exposed in `dynamic` workspace mode). |
| pipeline_type      | str  | The type of pipeline templates to list. Options: `query`, `indexing`.                                          |

The `list_templates`-tool returns a list of all templates in a workspace for the specified pipeline type. Templates are returned with their basic information including name, description, and use cases.

**Get Template**

| Parameter          | Type | Description                                                                                    |
|--------------------|------|------------------------------------------------------------------------------------------------|
| workspace          | str  | The name of the workspace to get the template from (only exposed in `dynamic` workspace mode). |
| template_name      | str  | The name of the template to get.                                                               |

The `get_template`-tool returns the full template object including its yaml configuration, description, name, use cases, and additional metadata.

**Search Templates**

| Parameter          | Type | Description                                                                                                    |
|--------------------|------|----------------------------------------------------------------------------------------------------------------|
| query              | str  | The search query to find matching templates.                                                                   |
| workspace          | str  | The name of the workspace to search templates in (only exposed in `dynamic` workspace mode).                  |
| top_k              | int  | The maximum number of template results to return (default: 10).                                                |
| pipeline_type      | str  | The type of pipeline templates to search. Options: `query`, `indexing`.                                        |

The `search_templates`-tool searches for templates based on the provided query. Returns matching templates ranked by relevance with their basic information and use cases.

#### Workspaces

**List Workspaces**

| Parameter | Type | Description |
|-----------|------|-------------|
| -         | -    | -           |

The `list_workspaces`-tool returns a list of all workspaces available to the user. Each workspace contains information about its name, ID, supported languages, and default idle timeout settings.

**Get Workspace**

| Parameter      | Type | Description                                                                                    |
|----------------|------|------------------------------------------------------------------------------------------------|
| workspace_name | str  | The name of the workspace to fetch details for.                                               |

The `get_workspace`-tool returns detailed information about a specific workspace, including its unique ID, supported languages, and configuration settings.

**Create Workspace**

| Parameter | Type | Description                                                                                    |
|-----------|------|------------------------------------------------------------------------------------------------|
| name      | str  | The name for the new workspace. Must be unique.                                               |

The `create_workspace`-tool creates a new workspace that can be used to organize pipelines, indexes, and other resources.
Returns success confirmation or error message.

#### Secrets

**List Secrets**

| Parameter | Type | Description                                                                                    |
|-----------|------|------------------------------------------------------------------------------------------------|
| limit     | int  | Maximum number of secrets to return (default: 10).                                            |

The `list_secrets`-tool retrieves a list of all secrets available in the user's deepset organization with their names and IDs.

**Get Secret**

| Parameter | Type | Description                                                                                    |
|-----------|------|------------------------------------------------------------------------------------------------|
| secret_id | str  | The unique identifier of the secret to retrieve.                                              |

The `get_secret`-tool retrieves detailed information about a specific secret by its ID. The secret value itself is not returned for security reasons, only metadata.

#### Object Store

**Get From Object Store**

| Parameter | Type | Description                                                                                    |
|-----------|------|------------------------------------------------------------------------------------------------|
| object_id | str  | The ID of the object to fetch in the format `@obj_001`.                                       |
| path      | str  | The path of the object to fetch in the format `access.to.attr` (optional).                   |
| workspace | str  | The name of the workspace (only exposed in `dynamic` workspace mode).                         |

The `get_from_object_store`-tool fetches an object from the object store. You can fetch a specific object by its ID or access nested paths within the object.

**Get Slice From Object Store**

| Parameter | Type | Description                                                                                    |
|-----------|------|------------------------------------------------------------------------------------------------|
| object_id | str  | Identifier of the object.                                                                      |
| start     | int  | Start index for slicing (default: 0).                                                         |
| end       | int  | End index for slicing (optional).                                                             |
| path      | str  | Navigation path to object to slice (optional).                                                |
| workspace | str  | The name of the workspace (only exposed in `dynamic` workspace mode).                         |

The `get_slice_from_object_store`-tool extracts a slice from a string or list object stored in the object store. Returns string representation of the slice.

#### Components

**List Component Families**

| Parameter | Type | Description |
|-----------|------|-------------|
| -         | -    | -           |

The `list_component_families`-tool returns a list of all Haystack component families available on deepset, with their names and descriptions.

**Search Component Definitions**

| Parameter | Type | Description                                                                                    |
|-----------|------|------------------------------------------------------------------------------------------------|
| query     | str  | The search query to find matching components.                                                 |
| top_k     | int  | Maximum number of results to return (default: 5).                                             |

The `search_component_definitions`-tool searches for components based on name or description using semantic similarity.
Returns matching components with similarity scores.

**Get Component Definition**

| Parameter      | Type | Description                                                                                    |
|----------------|------|------------------------------------------------------------------------------------------------|
| component_type | str  | Fully qualified component type (e.g., `haystack.components.routers.conditional_router.ConditionalRouter`). |

The `get_component_definition`-tool returns the detailed definition of a specific Haystack component, including its parameters, input and output connections, and documentation.

**Get Custom Components**

| Parameter | Type | Description                                                                                    |
|-----------|------|------------------------------------------------------------------------------------------------|
| workspace | str  | The name of the workspace (only exposed in `dynamic` workspace mode).                         |

The `get_custom_components`-tool returns a list of all installed custom components.

**List Custom Component Installations**

| Parameter | Type | Description                                                                                    |
|-----------|------|------------------------------------------------------------------------------------------------|
| workspace | str  | The name of the workspace (only exposed in `dynamic` workspace mode).                         |

The `list_custom_component_installations`-tool returns a list of custom component installations with their status and metadata.

**Get Latest Custom Component Installation Logs**

| Parameter | Type | Description                                                                                    |
|-----------|------|------------------------------------------------------------------------------------------------|
| workspace | str  | The name of the workspace (only exposed in `dynamic` workspace mode).                         |

The `get_latest_custom_component_installation_logs`-tool returns the logs from the latest custom component installation for debugging and monitoring purposes.

#### Documentation

**Search Docs**

| Parameter | Type | Description                                                                                    |
|-----------|------|------------------------------------------------------------------------------------------------|
| query     | str  | The search query to execute against the documentation.                                        |

The `search_docs`-tool allows you to search through deepset's official documentation to find information about features, API usage, best practices, and troubleshooting guides.
Returns formatted search results from the documentation.


## Known Limitations

This MCP server is in Beta. Please report any issues you may face through a GitHub Issue.
Feature requests and feedback are also appreciated.

**Updating Deployed Pipelines**

When a pipeline is deployed and updated through the `update_pipeline` tool, the update takes 30 to 300 seconds to apply.
The tool is currently returning before the pipeline update is applied. This may lead to situations where the Agent might have
already fixed an issue with a pipeline but when it tests it through search, the fix is not applied yet.
This might lead to the Agent repeatedly trying different update strategies, although no further action might be required.
You can check the state of the update in the pipeline logs. If "Application Startup Complete" appears in the logs,
the pipeline update should be applied.

**Deploying Indexes**

When an index is deployed, we are currently not waiting for the deployment to complete before returning a success message.
If the Agent deploys an index and tries a search immediately after, the search request may fail because the deployment is still in progress.
