# SDK Concepts

## About the Client-Resource Architecture

The Deepset API SDK is designed around a client-resource pattern that reflects how the deepset platform organizes its services.

At the core is the `AsyncDeepsetClient`, which serves as your gateway to the platform. The client exposes resource classes
for each platform component.

The resource classes themselves act as domain-specific interfaces.

Accessing resources through a shared client instance is easy by leveraging the built-in async context manager. Resources,
and connections are cleaned up automatically, as soon as we exit the context.

This design enables the SDK to provide both type safety and operational clarity.
Each resource class knows its domain deeply, while the client handles cross-cutting concerns like authentication and connection pooling.

## Understanding Resource Scoping

The platform distinguishes between two fundamental scoping patterns:

**Workspace-scoped resources** operate within specific project boundaries. This scoping exists because these resources often contain sensitive data, custom business logic, or project-specific configurations that shouldn't leak between environments:

- **Pipelines**: AI workflows containing your custom logic and data processing rules
- **Indexes**: Document storage systems with your proprietary data
- **Pipeline Templates**: Reusable configurations specific to your use cases
- **Custom Components**: Your domain-specific Haystack components

**Global resources** operate at the platform level because they represent shared infrastructure or account-level concerns:

- **Workspaces**: Project organization and isolation boundaries
- **Integrations**: Platform-wide service connections and credentials
- **Secrets**: Centralized credential management across projects
- **Users**: Account and identity management
- **Haystack Service**: Shared component schemas and metadata

This scoping model enables both isolation (workspace resources) and efficiency (global resources), allowing teams to work independently while sharing common platform services.

## Why Asynchronous by Design

The SDK's async-first design reflects the reality of modern AI applications. Unlike traditional CRUD operations, AI workloads involve:

- **Long-running operations**: Pipeline deployments and large document indexing
- **Streaming responses**: Real-time text generation and search results
- **High concurrency needs**: Processing multiple queries simultaneously
- **Variable response times**: AI operations can take seconds to minutes

Asynchronous operations allow your application to remain responsive during these long-running tasks. The async context manager pattern ensures proper resource cleanup, which is critical when dealing with HTTP connections and streaming responses.
