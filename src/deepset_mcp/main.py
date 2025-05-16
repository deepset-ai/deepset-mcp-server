import argparse
import os

from mcp.server.fastmcp import FastMCP
from model2vec import StaticModel

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.tools.haystack_service import (
    get_component_definition as get_component_definition_tool,
    list_component_families as list_component_families_tool,
    search_component_definition as search_component_definition_tool,
)
from deepset_mcp.tools.pipeline import (
    create_pipeline as create_pipeline_tool,
    get_pipeline as get_pipeline_tool,
    list_pipelines as list_pipelines_tool,
    update_pipeline as update_pipeline_tool,
    validate_pipeline as validate_pipeline_tool,
)
from deepset_mcp.tools.pipeline_template import (
    get_pipeline_template as get_pipeline_template_tool,
    list_pipeline_templates as list_pipeline_templates_tool,
)

INITIALIZED_MODEL = StaticModel.from_pretrained("minishlab/potion-base-2M")

# Initialize MCP Server
mcp = FastMCP("Deepset Cloud MCP")


def get_workspace() -> str:
    """Gets the workspace configured for the environment."""
    workspace = os.environ.get("DEEPSET_WORKSPACE")
    if not workspace:
        raise ValueError("DEEPSET_WORKSPACE environment variable not set")
    return workspace


@mcp.prompt()
async def deepset_platform() -> str:
    """System prompt for the deepset platform."""
    prompt = r"""
You are **deepset Copilot**, an AI Agent that helps developers build, inspect, and maintain Haystack pipelines on the
deepset AI Platform.

---

## 1. Core Concepts

### 1.1 Pipelines

* **Definition**: Ordered graphs of components that process data (queries, documents, embeddings, prompts, answers).
* **Flow**: Each component’s output becomes the next’s input.
* **Advanced Structures**:

  * **Branches**: Parallel paths (e.g., different converters for multiple file types).
  * **Loops**: Iterative cycles (e.g., self-correcting loops with a Validator).

**Full YAML Example**

````yaml
components:
  chat_summary_prompt_builder:
    type: haystack.components.builders.prompt_builder.PromptBuilder
    init_parameters:
      template: |-
        You are part of a chatbot.
        You receive a question (Current Question) and a chat history.
        Use the context from the chat history and reformulate the question so that it is suitable for retrieval
        augmented generation.
        If X is followed by Y, only ask for Y and do not repeat X again.
        If the question does not require any context from the chat history, output it unedited.
        Don't make questions too long, but short and precise.
        Stay as close as possible to the current question.
        Only output the new question, nothing else!

        {{ question }}

        New question:

      required_variables: "*"
  chat_summary_llm:
    type: deepset_cloud_custom_nodes.generators.deepset_amazon_bedrock_generator.DeepsetAmazonBedrockGenerator
    init_parameters:
      model: anthropic.claude-3-5-sonnet-20241022-v2:0
      aws_region_name: us-west-2
      max_length: 650
      model_max_length: 200000
      temperature: 0

  replies_to_query:
    type: haystack.components.converters.output_adapter.OutputAdapter
    init_parameters:
      template: "{{ replies[0] }}"
      output_type: str

  bm25_retriever: # Selects the most similar documents from the document store
    type: haystack_integrations.components.retrievers.opensearch.bm25_retriever.OpenSearchBM25Retriever
    init_parameters:
      document_store:
        type: haystack_integrations.document_stores.opensearch.document_store.OpenSearchDocumentStore
        init_parameters:
          embedding_dim: 768
      top_k: 20 # The number of results to return
      fuzziness: 0

  query_embedder:
    type: deepset_cloud_custom_nodes.embedders.nvidia.text_embedder.DeepsetNvidiaTextEmbedder
    init_parameters:
      normalize_embeddings: true
      model: intfloat/e5-base-v2

  embedding_retriever: # Selects the most similar documents from the document store
    type: haystack_integrations.components.retrievers.opensearch.embedding_retriever.OpenSearchEmbeddingRetriever
    init_parameters:
      document_store:
        type: haystack_integrations.document_stores.opensearch.document_store.OpenSearchDocumentStore
        init_parameters:
          embedding_dim: 768
      top_k: 20 # The number of results to return

  document_joiner:
    type: haystack.components.joiners.document_joiner.DocumentJoiner
    init_parameters:
      join_mode: concatenate

  ranker:
    type: deepset_cloud_custom_nodes.rankers.nvidia.ranker.DeepsetNvidiaRanker
    init_parameters:
      model: intfloat/simlm-msmarco-reranker
      top_k: 8

  meta_field_grouping_ranker:
    type: haystack.components.rankers.meta_field_grouping_ranker.MetaFieldGroupingRanker
    init_parameters:
      group_by: file_id
      subgroup_by: null
      sort_docs_by: split_id

  qa_prompt_builder:
    type: haystack.components.builders.prompt_builder.PromptBuilder
    init_parameters:
      template: |-
        You are a technical expert.
        You answer questions truthfully based on provided documents.
        If the answer exists in several documents, summarize them.
        Ignore documents that don't contain the answer to the question.
        Only answer based on the documents provided. Don't make things up.
        If no information related to the question can be found in the document, say so.
        Always use references in the form [NUMBER OF DOCUMENT] when using information from a document,
        e.g. [3] for Document [3] .
        Never name the documents, only enter a number in square brackets as a reference.
        The reference must only refer to the number that comes in square brackets after the document.
        Otherwise, do not use brackets in your answer and reference ONLY the number of the document without mentioning
        the word document.

        These are the documents:
        {%- if documents|length > 0 %}
        {%- for document in documents %}
        Document [{{ loop.index }}] :
        Name of Source File: {{ document.meta.file_name }}
        {{ document.content }}
        {% endfor -%}
        {%- else %}
        No relevant documents found.
        Respond with "Sorry, no matching documents were found, please adjust the filters or try a different question."
        {% endif %}

        Question: {{ question }}
        Answer:

      required_variables: "*"
  qa_llm:
    type: deepset_cloud_custom_nodes.generators.deepset_amazon_bedrock_generator.DeepsetAmazonBedrockGenerator
    init_parameters:
      model: anthropic.claude-3-5-sonnet-20241022-v2:0
      aws_region_name: us-west-2
      max_length: 650
      model_max_length: 200000
      temperature: 0

  answer_builder:
    type: deepset_cloud_custom_nodes.augmenters.deepset_answer_builder.DeepsetAnswerBuilder
    init_parameters:
      reference_pattern: acm

connections:  # Defines how the components are connected
- sender: chat_summary_prompt_builder.prompt
  receiver: chat_summary_llm.prompt
- sender: chat_summary_llm.replies
  receiver: replies_to_query.replies
- sender: replies_to_query.output
  receiver: bm25_retriever.query
- sender: replies_to_query.output
  receiver: query_embedder.text
- sender: replies_to_query.output
  receiver: ranker.query
- sender: replies_to_query.output
  receiver: qa_prompt_builder.question
- sender: replies_to_query.output
  receiver: answer_builder.query
- sender: bm25_retriever.documents
  receiver: document_joiner.documents
- sender: query_embedder.embedding
  receiver: embedding_retriever.query_embedding
- sender: embedding_retriever.documents
  receiver: document_joiner.documents
- sender: document_joiner.documents
  receiver: ranker.documents
- sender: ranker.documents
  receiver: meta_field_grouping_ranker.documents
- sender: meta_field_grouping_ranker.documents
  receiver: qa_prompt_builder.documents
- sender: meta_field_grouping_ranker.documents
  receiver: answer_builder.documents
- sender: qa_prompt_builder.prompt
  receiver: qa_llm.prompt
- sender: qa_prompt_builder.prompt
  receiver: answer_builder.prompt
- sender: qa_llm.replies
  receiver: answer_builder.replies

inputs:  # Define the inputs for your pipeline
  query:  # These components will receive the query as input
  - "chat_summary_prompt_builder.question"

  filters:  # These components will receive a potential query filter as input
  - "bm25_retriever.filters"
  - "embedding_retriever.filters"

outputs:  # Defines the output of your pipeline
  documents: "meta_field_grouping_ranker.documents"  # The output of the pipeline is the retrieved documents
  answers: "answer_builder.answers" # The output of the pipeline is the generated answers

### 1.2 Components
- **Identification**: Each has a unique `type` (fully qualified class path).
- **Configuration**: `init_parameters` control models, thresholds, credentials, etc.
- **I/O Signatures**: Named inputs and outputs, with specific data types (e.g., `List[Document]`, `List[Answer]`).

**Component Example**:
```yaml
my_converter:
  type: haystack.components.converters.xlsx.XLSXToDocument
  init_parameters:
    metadata_filters: ["*.sheet1"]
````

**Connection Example**:

```yaml
- sender: my_converter.documents
  receiver: text_converter.sources
```

### 1.3 YAML Structure

1. **components**: Declare each block’s name, `type`, and `init_parameters`.
2. **connections**: Link `sender:<component>.<output>` → `receiver:<component>.<input>`.
3. **inputs**: Map external inputs (`query`, `filters`) to component inputs.
4. **outputs**: Define final outputs (`documents`, `answers`) from component outputs.
5. **max\_loops\_allowed**: (Optional) Cap on loop iterations.

---

## 2. Agent Workflow

1. **Inspect & Discover**

   * Always call listing/fetch tools (`list_pipelines`, `get_component_definition`, etc.) to gather current state.
   * Check the pipeline templates, oftentimes you can start off of an existing template when the user wants to create a
        new pipeline.
   * Ask targeted questions if requirements are unclear.
2. **Architect Phase**

   * Draft a complete pipeline YAML or snippet.
   * Ask user: “Does this structure meet your needs?”
   * You MUST ask for confirmation before starting the Execution Phase.

3. **Execute Phase**

   * Validate with `validate_pipeline`.
   * Apply via `create_pipeline` or `update_pipeline`.
4. **Clarify & Iterate**

   * Ask targeted questions if requirements are unclear.
   * Loop back to Architect after clarifications.
5. **Integrity**

   * Never invent components; rely exclusively on tool-derived definitions.

---

## 3. Available Tools (brief)

* **Pipeline Management**:

  * `list_pipelines()`
  * `get_pipeline(pipeline_name)`
  * `create_pipeline(pipeline_name, yaml_configuration)`
  * `update_pipeline(pipeline_name, original_config, replacement_config)`
  * `validate_pipeline(yaml_configuration)`
* **Templates & Discovery**:

  * `list_pipeline_templates()`
  * `get_pipeline_template(template_name)`
* **Component Discovery**:

  * `list_component_families()`
  * `get_component_definition(component_type)`
  * `search_component_definitions(query)`

Use these tools for **every** action involving pipelines or components: gather definitions, draft configurations,
validate, and implement changes.
    """

    return prompt


@mcp.tool()
async def list_pipelines() -> str:
    """Retrieves a list of all pipeline available within the currently configured deepset workspace.

    Use this when you need to know the names or IDs of existing pipeline.
    This does not return the pipeline configuration.
    """
    workspace = get_workspace()
    async with AsyncDeepsetClient() as client:
        response = await list_pipelines_tool(client, workspace)

    return response


@mcp.tool()
async def list_pipeline_templates() -> str:
    """Retrieves a list of all pipeline templates available within the currently configured deepset workspace.

    Use this when you need to know the available pipeline templates and their capabilities.
    """
    workspace = get_workspace()
    async with AsyncDeepsetClient() as client:
        response = await list_pipeline_templates_tool(client, workspace)

    return response


@mcp.tool()
async def get_pipeline_template(template_name: str) -> str:
    """Fetches detailed configuration information for a specific pipeline template.

    This includes its YAML configuration, metadata, and recommended use cases.
    Use this when you need to inspect a specific template's structure or settings.

    :param template_name: Name of the pipeline template to retrieve.
    """
    workspace = get_workspace()
    async with AsyncDeepsetClient() as client:
        response = await get_pipeline_template_tool(client, workspace, template_name)

    return response


@mcp.tool()
async def get_pipeline(pipeline_name: str) -> str:
    """Fetches detailed configuration information for a specific pipeline, identified by its unique `pipeline_name`.

    This includes its components, connections, and metadata.
    Use this when you need to inspect the structure or settings of a known pipeline.

    :param pipeline_name: Name of the pipeline to retrieve.
    """
    workspace = get_workspace()
    async with AsyncDeepsetClient() as client:
        response = await get_pipeline_tool(client, workspace, pipeline_name)

    return response


@mcp.tool()
async def create_pipeline(pipeline_name: str, yaml_configuration: str) -> str:
    """Creates a new pipeline in deepset."""
    workspace = get_workspace()
    async with AsyncDeepsetClient() as client:
        response = await create_pipeline_tool(client, workspace, pipeline_name, yaml_configuration)

    return response


@mcp.tool()
async def update_pipeline(
    pipeline_name: str, original_configuration_snippet: str, replacement_configuration_snippet: str
) -> str:
    """Updates an existing pipeline in deepset.

    The update is performed by replacing the original configuration snippet with the new one.
    Make sure that your original snippet only has a single exact match in the pipeline configuration.
    Respect whitespace and formatting.
    """
    workspace = get_workspace()
    async with AsyncDeepsetClient() as client:
        response = await update_pipeline_tool(
            client=client,
            workspace=workspace,
            pipeline_name=pipeline_name,
            original_config_snippet=original_configuration_snippet,
            replacement_config_snippet=replacement_configuration_snippet,
        )

    return response


@mcp.tool()
async def list_component_families() -> str:
    """
    Returns a list of all component families available in deepset alongside their descriptions.

    Use this as a starting point for when you are unsure what types of components are available.
    """
    async with AsyncDeepsetClient() as client:
        response = await list_component_families_tool(client)

    return response


@mcp.tool()
async def get_component_definition(component_type: str) -> str:
    """Use this to get the full definition of a specific component.

    The component type is the fully qualified import path of the component class.
    For example: haystack.components.converters.xlsx.XLSXToDocument
    The component definition contains a description, parameters, and example usage of the component.
    """
    async with AsyncDeepsetClient() as client:
        response = await get_component_definition_tool(client, component_type)

    return response


@mcp.tool()
async def validate_pipeline(yaml_configuration: str) -> str:
    """
    Validates the structure and syntax of a provided pipeline YAML configuration against the deepset API specifications.

    Provide the YAML configuration as a string.
    Returns a validation result, indicating success or detailing any errors or warnings found.
    Use this *before* attempting to create or update a pipeline with new YAML.
    """
    workspace = get_workspace()

    async with AsyncDeepsetClient() as client:
        response = await validate_pipeline_tool(client, workspace, yaml_configuration)

    return response


@mcp.tool()
async def search_component_definitions(query: str) -> str:
    """Use this to search for components in deepset.

    You can use full natural language queries to find components.
    You can also use simple keywords.
    Use this if you want to find the definition for a component,
    but you are not sure what the exact name of the component is.
    """
    async with AsyncDeepsetClient() as client:
        response = await search_component_definition_tool(client=client, query=query, model=INITIALIZED_MODEL)

    return response


#
#
# @mcp.tool()
# async def get_custom_components() -> str:
#     """Use this to get a list of all installed custom components."""
#     response = await get_component_schemas()
#
#     # Check for errors in the response
#     if isinstance(response, dict) and "error" in response:
#         return f"Error retrieving component schemas: {response['error']}"
#
#     # Navigate to the components definition section
#     # Typically structured as {definitions: {Components: {<component_name>: <schema>}}}
#     schemas = response.get("component_schema", {})
#     schemas = schemas.get("definitions", {}).get("Components", {})
#
#     if not schemas:
#         return "No component schemas found or unexpected schema format."
#
#     # Filter for custom components (those with package_version key)
#     custom_components = {}
#     for component_name, schema in schemas.items():
#         if "package_version" in schema:
#             custom_components[component_name] = schema
#
#     if not custom_components:
#         return "No custom components found."
#
#     # Format the response
#     formatted_output = [f"# Custom Components ({len(custom_components)} found)\n"]
#
#     for component_name, schema in custom_components.items():
#         # Extract key information
#         package_version = schema.get("package_version", "Unknown")
#         dynamic_params = schema.get("dynamic_params", False)
#
#         # Get component type info
#         type_info = schema.get("properties", {}).get("type", {})
#         const_value = type_info.get("const", "Unknown")
#         family = type_info.get("family", "Unknown")
#         family_description = type_info.get("family_description", "No description")
#
#         # Format component details
#         component_details = [
#             f"## {component_name}",
#             f"- **Type**: `{const_value}`",
#             f"- **Package Version**: {package_version}",
#             f"- **Family**: {family} - {family_description}",
#             f"- **Dynamic Parameters**: {'Yes' if dynamic_params else 'No'}",
#         ]
#
#         # Add init parameters if available
#         init_params = schema.get("properties", {}).get("init_parameters", {}).get("properties", {})
#         if init_params:
#             component_details.append("\n### Init Parameters:")
#             for param_name, param_info in init_params.items():
#                 param_type = param_info.get("type", "Unknown")
#                 required = param_name in schema.get("properties", {}).get("init_parameters", {}).get("required", [])
#                 param_description = param_info.get("description", "No description")
#
#                 component_details.append(f"- **{param_name}** ({param_type}{', required' if required else ''}):")
#                 component_details.append(f"  {param_description}")
#
#         formatted_output.append("\n".join(component_details) + "\n")
#
#     # Join all sections and return
#     return "\n".join(formatted_output)
#
#
# @mcp.tool()
# async def get_latest_custom_component_installation_logs() -> Any:
#     """
#     Use this to get the logs from the latest custom component installation.
#
#     This will give you the full installation log output.
#     It is useful for debugging custom component installations.
#     """
#     async with AsyncDeepsetClient() as client:
#         return await client.request(endpoint="v2/custom_components/logs")
#
#
# @mcp.tool()
# async def list_custom_component_installations() -> str:
#     """
#     Retrieves a list of the most recent custom component installations.
#
#     This will return version number, high-level log, status and information about who uploaded the package.
#     """
#     endpoint = "v2/custom_components?limit=20&page_number=1&field=created_at&order=DESC"
#     async with AsyncDeepsetClient() as client:
#         resp = await client.request(endpoint=endpoint)
#
#         response = cast(dict[str, Any], resp.json)
#
#     installations = response.get("data", [])
#     total = response.get("total", 0)
#     has_more = response.get("has_more", False)
#
#     if not installations:
#         return "No custom component installations found."
#
#     # Format the response
#     formatted_output = [f"# Custom Component Installations (showing {len(installations)} of {total})\n"]
#
#     for install in installations:
#         # Extract key information
#         component_id = install.get("custom_component_id", "Unknown")
#         status = install.get("status", "Unknown")
#         version = install.get("version", "Unknown")
#         user_id = install.get("created_by_user_id", "Unknown")
#
#         # Try to fetch user information
#         user_info = "Unknown"
#         if user_id != "Unknown":
#             user_url = f"v1/users/{user_id}"
#             async with AsyncDeepsetClient() as client:
#                 user_response = await client.request(endpoint=user_url)
#
#             user_data = user_response.json
#             assert user_data is not None
#             given_name = user_data.get("given_name", "")
#             family_name = user_data.get("family_name", "")
#             email = user_data.get("email", "")
#             user_info = f"{given_name} {family_name} ({email})"
#
#         # Format installation details
#         install_details = [
#             f"## Installation {component_id[:8]}...",
#             f"- **Status**: {status}",
#             f"- **Version**: {version}",
#             f"- **Installed by**: {user_info}",
#         ]
#
#         # Add logs if available
#         logs = install.get("logs", [])
#         if logs:
#             install_details.append("\n### Recent Logs:")
#             for log in logs[:5]:  # Show only the first 5 logs
#                 level = log.get("level", "INFO")
#                 msg = log.get("msg", "No message")
#                 install_details.append(f"- [{level}] {msg}")
#
#             if len(logs) > 5:
#                 install_details.append(f"- ... and {len(logs) - 5} more log entries")
#
#         formatted_output.append("\n".join(install_details) + "\n")
#
#         if has_more:
#             formatted_output.append(
#                 "*Note: There are more installations available. This listing shows only the 10 most recent.*"
#             )
#
#     # Join all sections and return
#     return "\n".join(formatted_output)


def main():
    parser = argparse.ArgumentParser(
        description="Run the Deepset MCP server."
    )
    parser.add_argument(
        "--workspace", "-w",
        help="Deepset workspace (env DEEPSET_WORKSPACE)",
    )
    parser.add_argument(
        "--api-key", "-k",
        help="Deepset API key (env DEEPSET_API_KEY)",
    )
    args = parser.parse_args()

    # prefer flags, fallback to env
    workspace = args.workspace or os.getenv("DEEPSET_WORKSPACE")
    api_key   = args.api_key   or os.getenv("DEEPSET_API_KEY")
    if not workspace:
        parser.error("Missing workspace: set --workspace or DEEPSET_WORKSPACE")
    if not api_key:
        parser.error("Missing API key: set --api-key or DEEPSET_API_KEY")

    # make sure downstream tools see them
    os.environ["DEEPSET_WORKSPACE"] = workspace
    os.environ["DEEPSET_API_KEY"]    = api_key

    # run with SSE transport (HTTP+Server-Sent Events)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

