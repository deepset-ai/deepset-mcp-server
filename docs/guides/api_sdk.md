# Deepset API SDK

The Deepset API SDK provides a Python interface for interacting with the [deepset AI Platform](https://docs.cloud.deepset.ai/docs/getting-started). 
It enables developers to build, manage, and deploy AI-powered applications through a structured, asynchronous API.


## How-to Guides

### How to Set Up the Client

This guide shows you how to authenticate and configure the AsyncDeepsetClient for your environment.

**Using environment variables (recommended):**

```python
from deepset_mcp.api import AsyncDeepsetClient

# Reads DEEPSET_API_KEY from environment
async with AsyncDeepsetClient() as client:
    workspaces = await client.workspaces().list()
    print(f"Available workspaces: {len(workspaces)}")
```

**Providing credentials directly:**

```python
from deepset_mcp.api import AsyncDeepsetClient

async with AsyncDeepsetClient(api_key="your-api-key") as client:
    # Your code here
    pass
```

**Configuring for self-hosted instances:**

```python
from deepset_mcp.api import AsyncDeepsetClient

async with AsyncDeepsetClient(
    base_url="https://your-instance.deepset.ai/api"
) as client:
    # Your code here  
    pass
```

### How to Create and Deploy Pipelines

This guide shows you how to create, validate, and deploy AI pipelines from YAML configurations.

```python
from deepset_mcp.api import AsyncDeepsetClient

async with AsyncDeepsetClient() as client:
    pipelines = client.pipelines("my-workspace")
    
    # Create pipeline from YAML
    yaml_config = """
components:
  llm:
    type: haystack.components.generators.openai.OpenAIGenerator
    params:
      model: gpt-5
  answer_builder:
    type: haystack.components.builders.answer_builder.AnswerBuilder
connections:
    - sender: llm.replies
      receiver: answer_builder.replies
inputs:
    query:
        llm.prompt
        answer_builder.query
outputs:
    answers: answer_builder.answers
    """
    
    # Validate before creating
    validation = await pipelines.validate(yaml_config)
    if validation.valid:
        # Create the pipeline
        pipeline = await pipelines.create(
            pipeline_name="my-rag-pipeline",
            yaml_config=yaml_config
        )
        
        # Deploy the pipeline
        deployment = await pipelines.deploy("my-rag-pipeline")
        if deployment.valid:
            print("Pipeline deployed successfully!")
        else:
            print("Deployment failed:", deployment.errors)
```

### How to Search with Pipelines

This guide shows you how to perform both standard and streaming searches with deployed pipelines.

```python
from deepset_mcp.api import AsyncDeepsetClient

async with AsyncDeepsetClient() as client:
    pipelines = client.pipelines("my-workspace")
    
    # Standard search
    results = await pipelines.search(
        pipeline_name="my-rag-pipeline",
        query="What is artificial intelligence?",
        params={"top_k": 5},
    )
    
    # Real-time streaming search
    print("Streaming response:", end=" ")
    async for event in pipelines.search_stream(
        pipeline_name="my-rag-pipeline", 
        query="Explain machine learning"
    ):
        if event.type == "delta":
            print(event.delta.text, end="")
        elif event.type == "result":
            print(f"\n\nFinal result received: \n\n{event.result}")
```

### How to Create Indexes

This guide shows you how to set up indexes for RAG applications or other applications that need access to indexed data.

```python
from deepset_mcp.api import AsyncDeepsetClient

async with AsyncDeepsetClient() as client:
    indexes = client.indexes("my-workspace")
    
    # Create an index for document storage
    index_config = """
    document_store:
      type: WeaviateDocumentStore
      params:
        host: "http://localhost"
        port: 8080
    indexing_pipeline:
      type: Pipeline
      components:
        converter:
          type: TextFileToDocument
        embedder:
          type: SentenceTransformersDocumentEmbedder
          params:
            model: "sentence-transformers/all-MiniLM-L6-v2"
        writer:
          type: DocumentWriter
          params:
            document_store:
              type: WeaviateDocumentStore
              params:
                host: "http://localhost"
                port: 8080
    """
    
    await indexes.create(
        index_name="document-index",
        yaml_config=index_config,
        description="Document index for RAG pipeline"
    )
    
    await indexes.deploy(index_name="document-index")
```

### How to Organize Resources with Workspaces

Workspaces separate data, indexes, and pipelines.
This guide shows you how to create and manage workspaces for organizing your resources.

```python
from deepset_mcp.api import AsyncDeepsetClient

async with AsyncDeepsetClient() as client:
    workspaces_client = client.workspaces()
    
    # Create development and production workspaces
    await workspaces_client.create(name="development")
    await workspaces_client.create(name="production")
    
    # List all workspaces
    workspaces = await workspaces_client.list()
    for workspace in workspaces:
        print(f"Workspace: {workspace.name} (ID: {workspace.workspace_id})")
    
    # Use workspace-specific resources
    dev_pipelines = client.pipelines("development")
    prod_pipelines = client.pipelines("production")
```

### How to Use Pipeline Templates

This guide shows you how to find and use existing pipeline templates to accelerate development.

```python
from deepset_mcp.api import AsyncDeepsetClient

async with AsyncDeepsetClient() as client:
    templates = client.pipeline_templates("my-workspace")
    
    # Find suitable templates
    available_templates = await templates.list_templates(
        limit=10
    )
    
    # Use a template to create a pipeline
    if available_templates.data:
        template = await templates.get_template(available_templates.data[0].name)
        
        pipelines = client.pipelines("my-workspace")
        await pipelines.create(
            pipeline_name="pipeline-from-template",
            yaml_config=template.yaml_config
        )
```

### How to Handle Large Datasets with Pagination

This guide shows you how to work with paginated responses for large datasets using both automatic and manual approaches.

**Automatic iteration across all pages:**

```python
from deepset_mcp.api import AsyncDeepsetClient

async with AsyncDeepsetClient() as client:
    pipelines = client.pipelines("my-workspace")
    
    # Get first page
    paginator = await pipelines.list(limit=2)
    
    # Automatically iterate through ALL pages and items
    all_pipelines = []
    async for pipeline in paginator:  # Handles pagination automatically
        all_pipelines.append(pipeline)
        print(f"Processing pipeline: {pipeline.name}")
    
    print(f"Processed {len(all_pipelines)} total pipelines")
```

**Manual pagination with cursor control:**

If you need more control over pagination, you can use the `next_cursor` attribute on the `PaginatedResponse` to iterate
manually over pages.

```python
from deepset_mcp.api import AsyncDeepsetClient

async with AsyncDeepsetClient() as client:
    pipelines = client.pipelines("my-workspace")
    
    # Manual pagination using next_cursor
    current_page = await pipelines.list(limit=2)
    page_number = 1
    all_pipelines = []
    
    while current_page:
        print(f"Processing page {page_number}: {len(current_page.data)} pipelines")
        all_pipelines.extend(current_page.data)
        
        # Get next page manually using the cursor
        if current_page.has_more and current_page.next_cursor:
            current_page = await pipelines.list(limit=2, after=current_page.next_cursor)
            page_number += 1
        else:
            current_page = None
    
    print(f"Manual pagination: {len(all_pipelines)} total pipelines")
```


### How to Manage Secrets and Integrations

This guide shows you how to securely store API keys and configure external service integrations.

```python
from deepset_mcp.api import AsyncDeepsetClient

async with AsyncDeepsetClient() as client:
    # Manage secrets for API keys
    secrets_client = client.secrets()
    await secrets_client.create(
        name="openai-api-key",
        secret="sk-your-openai-key"
    )
    
    # Check available integrations
    integrations = client.integrations()
    available = await integrations.list()
    
    for integration in available.integrations:
        print(f"Provider: {integration.provider}")
        print(f"Domain: {integration.provider_domain}")
```

### How to Handle Errors

This guide shows you how to implement proper error handling for different types of API failures.

```python
from deepset_mcp.api import AsyncDeepsetClient
from deepset_mcp.api.exceptions import (
    BadRequestError,
    ResourceNotFoundError,
    UnexpectedAPIError
)

async with AsyncDeepsetClient() as client:
    pipelines = client.pipelines("my-workspace")
    
    try:
        pipeline = await pipelines.get("non-existent-pipeline")
    except ResourceNotFoundError:
        print("Pipeline not found - creating new one...")
        # Create pipeline logic here
    except BadRequestError as e:
        print(f"Invalid request parameters: {e}")
    except UnexpectedAPIError as e:
        print(f"API error occurred: {e}")
        # Log error and retry logic here
```

### How to Configure Custom Transport Settings

This guide shows you how to customize HTTP client behavior for specific requirements. The `transport_config` is passed 
through to `httpx.AsyncClient`. See all possible parameters in 
[their documentation](https://www.python-httpx.org/api/#asyncclient).

```python
from deepset_mcp.api import AsyncDeepsetClient

# Configure custom timeouts and retry behavior
transport_config = {
    "timeout": 60.0,  # 60 second timeout
    "headers": {
        "SOME-CUSTOM": "HEADER",
    }
}

async with AsyncDeepsetClient(
    transport_config=transport_config
) as client:
    # Client uses custom transport settings
    pass
```

### How to Debug and Monitor Pipelines

This guide shows you how to troubleshoot pipeline issues using debug information and logs.

```python
from deepset_mcp.api import AsyncDeepsetClient
from deepset_mcp.api.pipeline.models import LogLevel

async with AsyncDeepsetClient() as client:
    pipelines = client.pipelines("my-workspace")
    
    # Search with debugging enabled
    debug_results = await pipelines.search(
        pipeline_name="my-pipeline",
        query="test query",
        debug=True,           # Enable debug info
    )
    
    # Access debug information
    if debug_results.debug:
        print("Debug info:", debug_results.debug)
    
    # Get pipeline logs for troubleshooting
    logs = await pipelines.get_logs(
        pipeline_name="my-pipeline",
        limit=100,
        level=LogLevel.ERROR
    )
    
    for log_entry in logs.data:
        print(f"[{log_entry.timestamp}] {log_entry.level}: {log_entry.message}")
```

### How to Use in Synchronous Environments

This guide shows how to make API requests through the client in synchronous contexts.

```python
import asyncio
from deepset_mcp.api import AsyncDeepsetClient

client = AsyncDeepsetClient()
pipelines = client.pipelines("my-workspace")
my_pipeline = asyncio.run(pipelines.get("my-pipeline"))

valid = asyncio.run(pipelines.validate(my_pipeline.yaml_config))

if valid.valid:
    print("The pipeline is valid!")
```


