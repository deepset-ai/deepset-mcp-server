# MCP Server Concepts

This section explains key concepts that enable efficient AI tool orchestration between the deepset AI platform and various clients. Understanding these concepts helps you grasp why certain design decisions were made and how different components work together to create effective AI workflows.

## deepset AI Platform

The [deepset AI platform](https://www.deepset.ai/products-and-services/deepset-ai-platform) is a Software-as-a-Service solution for building and managing Large Language Model applications throughout their entire lifecycle. It serves as the foundation for creating AI-powered search and question-answering systems.

**Pipeline-Based Architecture**: The platform organizes AI functionality into pipelines—modular building blocks that can be mixed, matched, and replaced to form various configurations. Components like retrievers, generators, and processors connect together to create complete AI workflows. This flexibility allows you to customize behavior for different use cases while maintaining a consistent development experience.

**Model-Agnostic Design**: You can use all major LLMs in your applications without being locked into a specific vendor. The platform abstracts model differences, letting you switch between providers like OpenAI, Anthropic, or open-source models without rewriting your pipeline logic.

**Comprehensive Workflow Support**: The platform handles the entire AI application lifecycle—from data preprocessing and pipeline creation through evaluation, prototyping, deployment, and monitoring. This eliminates the need to stitch together separate tools for different development phases.

**Workspace Organization**: Multiple workspaces keep data and pipelines separate within an organization. Each workspace maintains its own indexes, files, and pipeline configurations, enabling clean separation between development, staging, and production environments.

The platform builds on Haystack, the open-source Python framework, providing a production-ready implementation with additional deepset-specific components and enterprise features.

## Model Context Protocol (MCP)

The [Model Context Protocol](https://modelcontextprotocol.io/docs/getting-started/intro) is an open standard that enables Large Language Models to connect with external data sources and tools in a consistent way. Think of MCP as a universal adapter that lets AI applications access diverse systems without custom integration code for each connection.

**Standardized Communication**: MCP defines how AI applications request information from external systems and how those systems respond. This standardization means that once you implement MCP support, your tools work with any MCP-compatible AI application—whether that's Claude Desktop, Cursor, or custom agents.

**Three-Layer Architecture**: MCP operates through three distinct components:

- **MCP Host**: The AI application (like Claude Desktop) that manages user interactions and orchestrates tool usage

- **MCP Client**: The protocol component that maintains connections to servers and handles communication

- **MCP Server**: Programs that expose specific capabilities like file access, database queries, or API interactions

**Capability Exchange**: Servers expose three types of capabilities to AI applications:

- **Tools**: Functions the AI can execute (like searching pipelines or creating indexes)

- **Resources**: Data sources the AI can read (like configuration files or documentation)

- **Prompts**: Template interactions that guide AI behavior

**Transport Flexibility**: MCP supports different communication methods—stdio transport for local processes and HTTP transport for remote services. This flexibility enables both desktop integrations and cloud-based deployments.

The protocol emphasizes human oversight and control, requiring user approval for tool executions while enabling sophisticated AI workflows across multiple specialized servers.

## Integrating deepset Platform with MCP Clients

MCP clients like Cursor, Claude Desktop, and Claude Code can connect to deepset platform capabilities through the deepset MCP server. This integration transforms how AI assistants interact with your search and AI pipeline infrastructure.

**Client-Side Configuration**: MCP clients require configuration files that specify how to connect to the deepset MCP server. These configurations include the execution command (typically `uvx deepset-mcp`), environment variables for authentication, and workspace settings. The client handles launching the server process and managing the connection lifecycle.

**Authentication Flow**: The integration supports both static API keys (set once in configuration) and dynamic authentication (extracted from request headers). Static authentication works well for single-user scenarios, while dynamic authentication enables multi-user deployments where different users access different deepset workspaces.

**Tool Discovery**: Once connected, MCP clients automatically discover available deepset tools—pipeline management, search operations, file uploads, and index creation. The client presents these tools to the AI assistant, which can then reason about when and how to use them based on user requests.

**Context Sharing**: The MCP protocol enables efficient sharing of complex data structures between tools. When a pipeline search returns large results, those results are stored in an object store rather than passed directly through the conversation. This approach prevents context window overflow while enabling sophisticated multi-step workflows.

**Workspace Flexibility**: Clients can be configured with a default workspace for all operations, or they can operate in dynamic mode where the AI assistant specifies the workspace for each tool invocation. This flexibility supports both focused single-project work and multi-environment management.

The integration creates a seamless experience where AI assistants can naturally work with your deepset platform resources, turning conversational requests like "search our documentation for deployment guides" into actual pipeline executions.

View our [installation guides](../installation.md) to set up the deepset MCP server with various MCP clients.

## Use with Custom Agents

Beyond MCP clients, the deepset MCP server tools can be used directly by custom AI agents that implement MCP client functionality. This approach enables building specialized AI applications that deeply integrate with deepset platform capabilities.

**Agent-Tool Interface**: AI agents can consume deepset MCP tools through the same protocol used by desktop clients. The tools are exposed as callable functions with typed parameters and structured return values, making them natural building blocks for agent workflows.

**Haystack Agent Integration**: Haystack provides a built-in MCPToolset that dynamically discovers and loads MCP server tools. This integration enables Haystack agents to use deepset platform capabilities alongside other tools in their workflows. The agent can reason about which tools to use, execute searches, analyze results, and take follow-up actions all within a single conversation.

**Custom Tool Orchestration**: When building custom agents, you can combine deepset MCP tools with other capabilities—web search, document processing, code execution, or domain-specific APIs. This combination creates powerful AI assistants that can bridge multiple systems while maintaining access to your deepset platform resources.

**Reference-Based Workflows**: The object store concept becomes particularly powerful in agent scenarios. Agents can chain operations together efficiently—search for documents, analyze the results, extract insights, and create new pipelines—all without re-transmitting large data structures between tool calls.

**Production Deployment**: Custom agents using deepset MCP tools can be deployed as remote services using HTTP transport. This enables building multi-user AI applications where different users access their own deepset workspaces through the same agent interface.

The flexibility of this approach means you can create everything from simple automation scripts that manage pipeline deployments to sophisticated AI assistants that help users explore and analyze their knowledge bases through natural conversation.

View [our guide](../guides/mcp_server.md#how-to-use-deepset-mcp-with-a-custom-haystack-agent) on how to integrate the deepset MCP package with a custom Haystack agent.

## Object Store

The Object Store is a key-value storage system that temporarily holds Python objects returned by tools. It addresses two critical challenges in AI tool orchestration:

**Context Window Management**: Large tool outputs can overwhelm the LLM's context window, making it impossible to process results effectively. The Object Store prevents this by storing complete objects separately from the conversation context.

**Cost and Performance Optimization**: When tools need to use outputs from previous tools, the LLM would normally regenerate that data, leading to increased costs and potential inconsistencies. The Object Store eliminates this redundancy by allowing direct data reuse.

### Storage Backends

The Object Store supports two backend implementations:

**In-Memory Backend** (`InMemoryBackend`): Stores objects in server memory with counter-based IDs (e.g., `obj_001`). Suitable for single-server deployments and development environments.

**Redis Backend** (`RedisBackend`): Uses Redis for distributed storage with UUID-based IDs (e.g., `obj_a7f3b2c1`). Required for multi-server deployments and production environments where persistence and scalability matter.

Both backends support configurable time-to-live (TTL) values to automatically clean up expired objects, preventing memory leaks in long-running deployments.

### Object Serialization

Objects are serialized using the `orjson` library for optimal performance. The serialization process handles:
- Pydantic models (using `model_dump()`)
- Sets and tuples (converted to lists)
- Nested objects with configurable depth limits

## Tool Output Truncation and Exploration

Tool output truncation addresses the challenge of presenting large, complex data structures to LLMs in a manageable format.

### The RichExplorer Component

The `RichExplorer` class generates human-readable, truncated representations of stored objects using the Rich library. It applies intelligent limits to prevent information overload:

**Collection Limits**: Lists and dictionaries are truncated after a configurable number of items (default: 25), with ellipsis indicating additional content.

**Depth Limits**: Nested structures are explored to a maximum depth (default: 4 levels) to prevent infinite expansion of complex hierarchies.

**String Truncation**: Long strings are cut at a configurable length (default: 300 characters) with clear truncation indicators.

**Context Headers**: Each output includes a header showing the object ID, type information, and size metadata (e.g., `@obj_123 → dict (length: 42)`).

### Exploration Tools

Two specialized tools enable LLMs to navigate stored objects:

**`get_from_object_store`**: Retrieves objects or specific nested properties using dot-notation paths (e.g., `@obj_123.config.timeout`). This tool provides the primary interface for accessing stored data.

**`get_slice_from_object_store`**: Extracts specific ranges from strings and lists (e.g., characters 100-200 of a document, items 10-20 of a list). This enables efficient inspection of large sequences without loading entire contents.

The distinction between these tools reflects different access patterns:
- Use `get_from_object_store` for structural navigation (accessing object properties)
- Use `get_slice_from_object_store` for range-based access (viewing portions of sequences)

## Tool Invocation by Reference

Tool invocation by reference enables tools to accept previously stored objects as parameters, eliminating the need to re-pass large data structures through the conversation.

### Reference Syntax

References use a consistent `@obj_id` or `@obj_id.path.to.property` format:
- `@obj_123` references an entire stored object
- `@obj_123.config.database_url` references a nested property
- Mixed usage: `validate_pipeline(config="@obj_123.pipeline_config", dry_run=True)`

### The @referenceable Decorator

Tools that accept references are decorated with `@referenceable`, which:

**Type System Integration**: Automatically modifies function signatures to accept string references alongside original parameter types. For example, a parameter `config: dict` becomes `config: dict | str`.

**Runtime Resolution**: Transparently resolves references to actual objects before function execution. The LLM sees the enhanced signature while the underlying function receives correctly typed objects.

**Validation**: Ensures non-reference strings are rejected for type-safe parameters, preventing accidental misuse.

**Path Validation**: Validates object paths using allow-list patterns to prevent unauthorized access to object internals.

### Workflow Optimization

Reference-based invocation creates efficient multi-step workflows:

1. **Initial Tool Call**: `get_pipeline("my-pipeline")` returns configuration stored as `@obj_123`
2. **Reference Usage**: `validate_pipeline(config="@obj_123.pipeline_config")` processes the configuration without re-transmission
3. **Cost Reduction**: Eliminates token costs for re-generating large YAML configurations, API responses, or data structures
4. **Consistency**: Prevents subtle errors from LLM re-generation of complex data

### Decorator Combinations

The system provides three decorator patterns:

**`@explorable`**: Tools store outputs in the Object Store for later reference
**`@referenceable`**: Tools accept object references as input parameters  
**`@explorable_and_referenceable`**: Tools both accept references and store outputs, enabling chainable workflows

These decorators work together to create seamless data flow between tools while maintaining type safety and performance optimization.

View [our in-depth guides](../guides/mcp_server.md#how-to-create-custom-referenceable-and-explorable-tools) on how to work with the object store and tool invocation by reference.