# deepset API SDK

The deepset API SDK provides a comprehensive Python interface for interacting with the deepset AI Platform. It simplifies the process of building, managing, and deploying AI-powered applications by providing structured access to all platform resources.

## Getting Started

The SDK is built around the `AsyncDeepsetClient`, which provides access to different resources on the deepset platform. All operations are asynchronous and use modern Python async/await patterns for optimal performance.

### Installation and Setup

Initialize the client with your API key:

```python
from deepset_mcp.api.client import AsyncDeepsetClient

# Using environment variable DEEPSET_API_KEY
async with AsyncDeepsetClient() as client:
    # Your code here
    pass

# Or provide API key directly
async with AsyncDeepsetClient(api_key="your-api-key") as client:
    # Your code here
    pass
```

The client automatically handles authentication, request management, and connection pooling. Always use it as an async context manager to ensure proper resource cleanup.

## Core Resources

The SDK provides access to nine main resources, each designed for specific aspects of the deepset platform:

### Pipelines

Pipelines are the core building blocks of your AI applications. They define how data flows through different components to produce results.

```python
from deepset_mcp.api.client import AsyncDeepsetClient

async with AsyncDeepsetClient() as client:
    # Access pipeline resource for a specific workspace
    pipelines = client.pipelines(workspace="your-workspace")
    
    # List all pipelines
    pipeline_list = await pipelines.list(page_number=1, limit=10)
    
    # Get a specific pipeline with its YAML configuration
    pipeline = await pipelines.get("my-pipeline", include_yaml=True)
    
    # Create a new pipeline
    yaml_config = """
    components:
      text_embedder:
        type: SentenceTransformersTextEmbedder
        params:
          model: "sentence-transformers/all-MiniLM-L6-v2"
    """
    
    response = await pipelines.create(
        name="my-new-pipeline",
        yaml_config=yaml_config
    )
```

### Pipeline Management

The SDK provides comprehensive pipeline lifecycle management:

```python
from deepset_mcp.api.client import AsyncDeepsetClient

yaml_config = "some: yaml"
updated_yaml_config = "some: other yaml"

async with AsyncDeepsetClient() as client:
    # Access pipeline resource for a specific workspace
    pipelines = client.pipelines(workspace="your-workspace")

    # Validate a pipeline configuration before deployment
    validation_result = await pipelines.validate(yaml_config)
    if validation_result.valid:
        print("Pipeline configuration is valid")
    else:
        for error in validation_result.errors:
            print(f"Error {error.code}: {error.message}")
    
    # Update an existing pipeline
    await pipelines.update(
        pipeline_name="my-pipeline",
        updated_pipeline_name="my-renamed-pipeline",  # Optional
        yaml_config=updated_yaml_config  # Optional
    )
    
    # Deploy a pipeline to production
    deployment_result = await pipelines.deploy("my-pipeline")
    
    # Delete a pipeline
    await pipelines.delete("my-pipeline")
```

### Search and Streaming

Execute searches using deployed pipelines:

```python
from deepset_mcp.api.client import AsyncDeepsetClient

async with AsyncDeepsetClient() as client:
    pipelines = client.pipelines(workspace="your-workspace")
    
    # Basic search
    search_response = await pipelines.search(
        pipeline_name="my-pipeline",
        query="What is artificial intelligence?",
        debug=True,  # Include debug information
        view_prompts=True,  # Include prompts in response
        params={"top_k": 5},  # Pipeline-specific parameters
        filters={"category": "AI"}  # Search filters
    )
    
    # Streaming search for real-time results
    async for event in pipelines.search_stream(
        pipeline_name="my-pipeline",
        query="What is artificial intelligence?",
        debug=True
    ):
        if event.type == "delta":
            print(event.delta.text, end="")
        elif event.type == "result":
            print(f"\nFinal result: {event.result}")
```

### Pipeline Monitoring

Monitor pipeline performance and troubleshoot issues:

```python
from deepset_mcp.api.pipeline.log_level import LogLevel
from deepset_mcp.api.client import AsyncDeepsetClient


async with AsyncDeepsetClient() as client:
    pipelines = client.pipelines(workspace="your-workspace")
    # Get pipeline logs
    logs = await pipelines.get_logs(
        pipeline_name="my-pipeline",
        limit=50,
        level=LogLevel.ERROR  # Filter by log level
    )
    
    for log_entry in logs.data:
        print(f"[{log_entry.level}] {log_entry.message}")
```

### Indexes

Indexes store and organize your data for efficient retrieval:

```python
from deepset_mcp.api.client import AsyncDeepsetClient

async with AsyncDeepsetClient() as client:
    indexes = client.indexes(workspace="your-workspace")
    
    # List all indexes
    index_list = await indexes.list()
    
    # Get a specific index
    index = await indexes.get("my-index")
    
    # Create a new index
    index_yaml = """
    document_store:
      type: InMemoryDocumentStore
    indexing_pipeline:
      type: Pipeline
      components:
        converter:
          type: TextFileToDocument
    """
    
    await indexes.create(
        name="my-new-index",
        yaml_config=index_yaml,
        description="My document index"
    )
    
        updated_yaml = """
    document_store:
      type: OpenSearchDocumentStore
    indexing_pipeline:
      type: Pipeline
      components:
        converter:
          type: TextFileToDocument
    """
    
    # Update an existing index
    await indexes.update(
        index_name="my-index",
        updated_index_name="my-renamed-index",
        yaml_config=updated_yaml
    )
```

### Pipeline Templates

Templates provide pre-built pipeline configurations for common use cases:

```python
from deepset_mcp.api.client import AsyncDeepsetClient

async with AsyncDeepsetClient() as client:
    templates = client.pipeline_templates(workspace="your-workspace")
    
    # List available templates
    template_list = await templates.list_templates(
        limit=20,
        field="created_at",
        order="DESC",
        filter="category eq 'RAG'"  # OData filter
    )
    
    # Get a specific template with its YAML configuration
    template = await templates.get_template("template-name")
    
    # Use the template YAML to create a new pipeline
    if template.yaml_config:
        pipelines = client.pipelines(workspace="your-workspace")
        await pipelines.create(
            name="pipeline-from-template",
            yaml_config=template.yaml_config
        )
```

### Haystack Service

Access Haystack component definitions and schemas:

```python
from deepset_mcp.api.client import AsyncDeepsetClient

async with AsyncDeepsetClient() as client:
    haystack = client.haystack_service()
    
    # Get all component schemas
    schemas = await haystack.get_component_schemas()
    
    # Get input/output information for a specific component
    io_info = await haystack.get_component_input_output("ConditionalRouter")
    
    print(f"Component inputs: {io_info.inputs}")
    print(f"Component outputs: {io_info.outputs}")
```

### Custom Components

Manage custom component installations:

```python
from deepset_mcp.api.client import AsyncDeepsetClient

async with AsyncDeepsetClient() as client:
    custom_components = client.custom_components(workspace="your-workspace")
    
    # List installed custom components
    installations = await custom_components.list_installations()
    
    for installation in installations.data:
        print(f"Component: {installation.custom_component_id}")
        print(f"Status: {installation.status}")
        print(f"Version: {installation.version}")
```

### Integrations

Manage external service integrations:

```python
from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.api.integrations.models import IntegrationProvider

async with AsyncDeepsetClient() as client:
    integrations = client.integrations()
    
    # List all integrations
    integration_list = await integrations.list()
    
    for integration in integration_list.integrations:
        print(f"Provider: {integration.provider}")
        print(f"Domain: {integration.provider_domain}")
        
    # Get a specific integration by provider
    openai_integration = await integrations.get(IntegrationProvider.OPENAI)
    print(f"OpenAI Integration: {openai_integration.provider_domain}")
```

### Secrets

Manage secrets for secure configuration and sensitive data:

```python
from deepset_mcp.api.client import AsyncDeepsetClient

async with AsyncDeepsetClient() as client:
    secrets = client.secrets()
    
    # List all secrets
    secret_list = await secrets.list(
        limit=20,
        field="created_at",
        order="DESC"
    )
    
    # Create a new secret
    await secrets.create(
        name="api-key-secret",
        secret="your-secret-value"
    )
    
    # Get a specific secret
    secret = await secrets.get("secret-id")
    print(f"Secret name: {secret.name}")
    
    # Delete a secret
    await secrets.delete("secret-id")
```

### Users

Access user information and manage user-related operations:

```python
from deepset_mcp.api.client import AsyncDeepsetClient


async with AsyncDeepsetClient() as client:
    users = client.users()
    
    # Get user information
    user = await users.get("user-id")
    print(f"User: {user.given_name} {user.family_name}")
    print(f"Email: {user.email}")
```

### Workspaces

Manage workspaces to organize your projects and resources:

```python
from deepset_mcp.api.client import AsyncDeepsetClient

async with AsyncDeepsetClient() as client:
    workspaces = client.workspaces()
    
    # List all workspaces
    workspace_list = await workspaces.list()
    
    for workspace in workspace_list.data:
        print(f"Workspace: {workspace.name}")
        print(f"ID: {workspace.workspace_id}")
        print(f"Default timeout: {workspace.default_idle_timeout_in_seconds}s")
    
    # Get a specific workspace
    workspace = await workspaces.get("my-workspace")
    print(f"Languages: {workspace.languages}")
    
    # Create a new workspace
    await workspaces.create(name="new-workspace")
    
    # Delete a workspace
    await workspaces.delete("old-workspace")
```

## Advanced Configuration

### Custom Transport

For advanced use cases, you can provide custom transport configuration:

```python
from deepset_mcp.api.client import AsyncDeepsetClient

transport_config = {
    "timeout": 30,  # Request timeout in seconds
    "retries": 3,   # Number of retries
}

async with AsyncDeepsetClient(
    transport_config=transport_config
) as client:
    # Your code here
    pass
```

### Error Handling

The SDK provides specific exceptions for different error conditions:

```python
from deepset_mcp.api.exceptions import (
    BadRequestError,
    ResourceNotFoundError,
    UnexpectedAPIError
)

from deepset_mcp.api.client import AsyncDeepsetClient


async with AsyncDeepsetClient() as client:
    pipelines = client.pipelines(workspace="your-workspace")

    try:
        pipeline = await pipelines.get("non-existent-pipeline")
    except ResourceNotFoundError:
        print("Pipeline not found")
    except BadRequestError as e:
        print(f"Bad request: {e}")
    except UnexpectedAPIError as e:
        print(f"Unexpected error: {e}")
```

## Best Practices

### Resource Management

Always use the client as an async context manager to ensure proper cleanup:

```python
from deepset_mcp.api.client import AsyncDeepsetClient

# Good - automatically handles resource cleanup
async with AsyncDeepsetClient() as client:
    result = await client.pipelines("workspace").list()

# Avoid - requires manual cleanup
client = AsyncDeepsetClient()
try:
    result = await client.pipelines("workspace").list()
finally:
    await client.close()
```

### Workspace Organization

Organize your resources by workspace for better management:

```python
from deepset_mcp.api.client import AsyncDeepsetClient

async with AsyncDeepsetClient() as client:
    # Development workspace
    dev_pipelines = client.pipelines("development")
    dev_pipeline = await dev_pipelines.create(name="test-pipeline", yaml_config=config)
    
    # Production workspace
    prod_pipelines = client.pipelines("production")
    prod_pipeline = await prod_pipelines.create(name="prod-pipeline", yaml_config=config)
```

### Validation Before Deployment

Always validate pipeline configurations before deployment:

```python
from deepset_mcp.api.client import AsyncDeepsetClient


async with AsyncDeepsetClient() as client:
    pipelines = client.pipelines(workspace="your-workspace")

    # Validate configuration
    validation_result = await pipelines.validate(yaml_config)
    
    if validation_result.valid:
        # Create and deploy pipeline
        await pipelines.create(name="my-pipeline", yaml_config=yaml_config)
        deployment_result = await pipelines.deploy("my-pipeline")
        
        if deployment_result.valid:
            print("Pipeline deployed successfully")
        else:
            print("Deployment failed:", deployment_result.errors)
    else:
        print("Configuration invalid:", validation_result.errors)
```

### Streaming for Real-Time Applications

Use streaming for applications that need real-time responses:

```python
async def stream_search_results(pipelines, query):
    async for event in pipelines.search_stream(
        pipeline_name="chat-pipeline",
        query=query
    ):
        if event.type == "delta":
            # Stream partial results to user
            yield event.delta.text
        elif event.type == "result":
            # Final result available
            return event.result
        elif event.error:
            # Handle streaming errors
            raise Exception(event.error)
```

## API Reference

### AsyncDeepsetClient

Main client class for API access.

**Constructor Parameters:**
- `api_key` (str, optional): API key for authentication. Falls back to `DEEPSET_API_KEY` environment variable.
- `base_url` (str, optional): Base URL for the API. Defaults to `https://api.cloud.deepset.ai/api`.
- `transport` (TransportProtocol, optional): Custom transport implementation.
- `transport_config` (dict, optional): Configuration for default transport.

**Resource Methods:**
- `pipelines(workspace: str)`: Returns PipelineResource for the specified workspace
- `indexes(workspace: str)`: Returns IndexResource for the specified workspace
- `pipeline_templates(workspace: str)`: Returns PipelineTemplateResource for the specified workspace
- `custom_components(workspace: str)`: Returns CustomComponentsResource for the specified workspace
- `integrations()`: Returns IntegrationResource
- `haystack_service()`: Returns HaystackServiceResource
- `secrets()`: Returns SecretResource
- `users()`: Returns UserResource
- `workspaces()`: Returns WorkspaceResource for workspace management

### Resource Classes

Each resource class provides methods specific to that resource type. All methods are async and return appropriate response models.

For detailed method signatures and response models, refer to the type hints in the source code or use your IDE's autocomplete functionality.
