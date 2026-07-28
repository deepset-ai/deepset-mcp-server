# Tool Reference

## MCP tool names

The tables below list every tool the MCP server can expose, by its MCP tool name. MCP tool name is the name an
agent calls and the name you pass to `tools_to_register`:

```python
configure_mcp_server(
    mcp_server_instance=mcp,
    tools_to_register={"list_pipelines", "get_pipeline", "grep_object_store"},
)
```

!!! note

    A few MCP tool names differ from the Python function that implements them (the function is what
    appears under [Tool base functions](#tool-base-functions) below). Always register the **MCP tool
    name** listed in this table:

    | MCP tool name | Implemented by Python function |
    | --- | --- |
    | `search_component_definitions` | `search_component_definition` |
    | `get_from_object_store` | `create_get_from_object_store` |
    | `get_slice_from_object_store` | `create_get_slice_from_object_store` |
    | `grep_object_store` | `create_grep_object_store` |
    | `sed_object_store` | `create_sed_object_store` |
    | `yq_object_store` | `create_yq_object_store` |
    | `search_docs` | `get_docs_search_tool` |


### Pipelines

The *Memory* column describes how a tool interacts with the object store (see
[MCP server concepts](../concepts/mcp_server_concepts.md)):

- *explorable*: The tool's output is stored and returned as an `@obj_id` reference.
- *referenceable*: The tool accepts `@obj_id` references as parameters.
- *none*: The tool returns its output directly.

| MCP tool name | Workspace | Memory | Description |
| --- | --- | --- | --- |
| `list_pipelines` | required | explorable | List all pipelines in the workspace. |
| `get_pipeline` | required | explorable | Fetch a pipeline's configuration and status. |
| `create_pipeline` | required | explorable, referenceable | Create a new pipeline from a YAML configuration. |
| `validate_pipeline` | required | explorable, referenceable | Validate a YAML configuration without saving it. |
| `deploy_pipeline` | required | explorable | Deploy a pipeline and wait for it to become available. |
| `get_pipeline_logs` | required | explorable | Fetch a deployed pipeline's logs. |
| `search_pipeline` | required | explorable | Run a query against a deployed pipeline. |
| `search_pipeline_with_filters` | required | explorable | Run a query with metadata filters. |
| `search_pipeline_with_params` | required | explorable | Run a query with component-level parameter overrides. |

### Pipeline versions

| MCP tool name | Workspace | Memory | Description |
| --- | --- | --- | --- |
| `list_pipeline_versions` | required | explorable | List a pipeline's saved versions. |
| `get_pipeline_version` | required | explorable | Fetch a specific pipeline version. |
| `create_pipeline_version` | required | explorable, referenceable | Save the current configuration as a new version. |
| `patch_pipeline_version` | required | explorable, referenceable | Apply a partial update to a pipeline version. |
| `restore_pipeline_version` | required | explorable, referenceable | Restore a pipeline to an earlier version. |

### Indexes

| MCP tool name | Workspace | Memory | Description |
| --- | --- | --- | --- |
| `list_indexes` | required | explorable | List all indexes in the workspace. |
| `get_index` | required | explorable | Fetch an index's configuration. |
| `create_index` | required | explorable, referenceable | Create a new index from a YAML configuration. |
| `update_index` | required | explorable, referenceable | Update an existing index's configuration. |
| `validate_index` | required | explorable, referenceable | Validate an index configuration without saving it. |
| `deploy_index` | required | explorable | Deploy an index. |

### Search history and traces

| MCP tool name | Workspace | Memory | Description |
| --- | --- | --- | --- |
| `list_search_history` | required | explorable | List search history across the workspace. |
| `list_pipeline_search_history` | required | explorable | List search history for one pipeline. |
| `list_pipeline_traces` | required | explorable | List lightweight run-trace summaries for a pipeline. |
| `get_pipeline_trace` | required | explorable | Fetch the full execution trace for one query, including component spans with input/output and logs. |
| `get_pipeline_trace_span_tags` | required | explorable | Fetch the tags of a single span, to inspect one component's input/output cheaply. |
| `get_pipeline_trace_logs` | required | explorable | Fetch only the log entries for one run. |

### Templates

| MCP tool name | Workspace | Memory | Description |
| --- | --- | --- | --- |
| `list_templates` | required | explorable | List available pipeline templates. |
| `get_template` | required | explorable | Fetch a specific pipeline template. |
| `search_templates` | required | explorable | Search templates by semantic similarity. |

### Haystack components

| MCP tool name | Workspace | Memory | Description |
| --- | --- | --- | --- |
| `list_component_families` | not needed | explorable | List the available Haystack component families. |
| `get_component_definition` | not needed | explorable | Fetch a component's initialization parameters and I/O. |
| `search_component_definitions` | not needed | explorable | Search component definitions by semantic similarity. |
| `get_custom_components` | not needed | explorable | List the custom components installed for the organization. |
| `run_component` | not needed | explorable, referenceable | Run a single component in isolation to test its behavior. |

### Custom components

| MCP tool name | Workspace | Memory | Description |
| --- | --- | --- | --- |
| `list_custom_component_installations` | required | explorable | List custom component installations. |
| `get_latest_custom_component_installation_logs` | required | explorable | Fetch logs for the most recent custom component installation. |

### Workspaces, secrets and models

| MCP tool name | Workspace | Memory | Description |
| --- | --- | --- | --- |
| `list_workspaces` | not needed | explorable | List the workspaces available to the API key. |
| `get_workspace` | not needed | explorable | Fetch a workspace's details. |
| `create_workspace` | not needed | explorable | Create a new workspace. |
| `list_secrets` | not needed | explorable | List the secrets available to the organization. |
| `get_secret` | not needed | explorable | Fetch a secret's metadata by ID. |
| `get_models` | required | explorable | List models available for use in pipelines. |

### Object store

These tools let an agent inspect and manipulate stored objects without pulling them into context.
See [Tool output truncation and exploration](../concepts/mcp_server_concepts.md#tool-output-truncation-and-exploration).

| MCP tool name | Workspace | Memory | Description |
| --- | --- | --- | --- |
| `get_from_object_store` | not needed | none | Fetch a stored object, or a nested value by path. |
| `get_slice_from_object_store` | not needed | none | Extract a range from a stored string or list. |
| `grep_object_store` | not needed | none | Regex-search a stored string and return matches with context. |
| `sed_object_store` | not needed | none | Regex-replace within a stored string, storing the result as a new object. |
| `yq_object_store` | not needed | none | Query or transform stored YAML/JSON with a `jq` filter expression. |

### Documentation and skills

| MCP tool name | Workspace | Memory | Description |
| --- | --- | --- | --- |
| `search_docs` | not needed | none | Search the Haystack Enterprise Platform documentation. Requires docs search to be configured on the server. |
| `load_skill` | not needed | none | Load a bundled skill containing detailed guidance for a specific task. |

## Tool base functions

The Python functions that implement the tools above. Their docstrings are what the calling LLM
receives as the tool description.

::: deepset_mcp.tools
    options:
        show_submodules: false
        heading_level: 3
        filters: [ "!^_(?!_init__)" ]
