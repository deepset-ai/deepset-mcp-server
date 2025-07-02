## Overview

`deepset-mcp-server` provides an API SDK and MCP (model context protocol) tools to interact with the deepset API.
deepset is an AI platform that allows users to develop and deploy AI applications.
All applications are defined as Haystack pipelines.
Haystack is an Open Source Python framework for AI application building.

## Project Structure

All source code is in `src/deepset_mcp`.
Code for the API SDK is in `src/deepset_mcp/api`.
Code for tools is in `src/deepset_mcp/tools`.
The tools are added to an MCP server which is defined in `src/deepset_mcp/main.py` and configured in `src/deepset_mcp/tool_factory.py`.

Tests are in the `test` directory.
All unit tests go into `test/unit`, integration tests go into `test/integration`.

We use uv to manage the project.
All project level configurations are defined in `pyproject.toml` at the root of the repository.

### API SDK structure

The API SDK is 'async first'.
All API interactions run through a common facade called `AsyncDeepsetClient`.
The client exposes resources that in turn expose methods to interact with these resources through the deepset API.

As an example, to fetch a specific pipeline a user might do:

```python
from deepset_mcp.api.client import AsyncDeepsetClient

async with AsyncDeepsetClient() as client:
  response = await client.pipelines(workspace="some_workspace").get("my_pipeline")

```

### Tool Structure

Tools are meant to be used by large language models.
Known exceptions should usually be caught and converted to strings.
Typically, we have one tool file per resource.
A tool can make multiple calls to different resources or different methods on the same resource to produce the desired output.
Most tools are imported into `src/deepset_mcp/tool_factory.py` where they are added to the MCP server.


## Instructions for common tasks

### Task: Adding a new resource

Let's assume we want to add a `PipelineFeedbackResource`.
You would need to make the following changes:

1. add a package for the resource at `src/deepset_mcp/api/pipeline_feedback`
2. the resource goes into `src/deepset_mcp/api/pipeline_feedback/resource.py`
3. (optional) if you need to define models for API response they would go into `src/deepset_mcp/api/pipeline_feedback/models.py`
4. add a Protocol for the resource in `src/deepset_mcp/api/pipeline_feedback/protocols.py`
5. add the resource to the AsyncClientProtocol in the `src/deepset_mcp/api/protocols.py` (depending on the resource you need client and workspace or just client)
6. add a method for the resource to the `AsyncDeepsetClient` in `src/deepset_mcp/api/client.py`

#### Testing the resource
Each resource gets unit and integration tests for all methods.

1. first add a stub for the resource to the `BaseFakeClient` in `test/unit/conftest.py`
2. create a directory for the unit tests in `test/unit/api/` (i.e. `test/unit/api/pipeline_feedback`)
3. we use pytest for all unit tests
4. import the `BaseFakeClient` from `test/unit/conftest.py`
5. Overwrite the `pipeline_feedback`-method on the client so that it returns your actual `PipelineFeedbackResource`
6. Add fake responses to the client according to what you want to test
7. Create comprehensive unit tests
8. all tests must have complete type hints including return types
9. `test/unit/api/haystack_service/test_haystack_service_resource.py` has a good example of how to structure unit tests for a resource

10. integration tests go into `test/integration`
11. create an integration test file at `test/integration/test_integration_pipeline_feedback_resource.py`
12. `test/integration/test_integration_haystack_service_resource.py` has a good example for how integration tests may look like
13. don't add too many integration tests, they are mostly a sanity check, the bulk of the testing should be written as unit tests

### Task: Adding a new tool

Let's assume we want to add a `fetch_pipeline_resource`-tool that will use our newly added resource.
You would need to perform the following steps:

1. the tool would go into `src/deepset_mcp/tools/pipeline_feedback.py`
2. the client will ALWAYS be passed to the tool as a dependency injection (type: `AsyncClientProtocol`)
3. the tool should call the methods on the resource through the client
4. refer to `src/deepset_mcp/tools/pipeline.py` as a good example for tool implementations
5. extract model or response serialization into reusable helper functions
6. once you added a tool, import it in `src/deepset_mcp/tool_factory.py` and add it to the tool registry with the appropriate config
7. the docstring of the tool will serve as the prompt for the large language model calling the tool, make sure it has good instructions on when to use the tool, how to best use it, and what kind of answer to expect.

#### Testing the tool

We ONLY add unit tests for the tool. The mcp integration will not have tests.

1. the tool tests will go into `test/unit/tools` (i.e. `test/unit/tools/test_pipeline_feedback.py`)
2. use a FakeResource to test the tool
3. import the `BaseFakeClient` and overwrite the resource method to return your fake resource
4. `test/unit/tools/test_pipeline.py` has a good example for how to test a tool


## Code Style Guidelines

- Our code is clean and maintainable
- Pay attention to great code structure and optimize for readability
- We use mypy (strict) and ruff for type checking and linting
- Docstrings MUST follow the reStructuredText style (this is a new change and many docstrings follow a different style)
Example:
```python
def foo(arg1: Type1, arg2: Type2) -> ReturnType:
    """Returns the result of fooing ``arg1`` with ``arg2``.

    :param arg1: A good argument.
    :param arg2: Another good argument.

    :returns: Some nifty thing or other.
    """
```
- We use Python 3.12
- We use many modern code constructs throughout the code base (Protocols, Generics, Dependency Injection)
- Generally follow the coding style that you are already observing throughout the code base


## Contributions

- keep changes minimal and only implement what was requested in the issue
- all changes need to be tested according to our testing guidelines
- use clear commit messages following the conventional commits style
- we typically make changes in relatively small PRs (e.g. 1 PR for adding a resource and another PR for adding the tools)
- use docstrings, add comments only where needed, follow our code style guidelines
- be kind!

  
