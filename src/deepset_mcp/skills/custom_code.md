---
name: custom-code
description: Use this skill whenever writing, generating, reviewing, or fixing a Haystack custom component or custom tool for the deepset/Haystack enterprise platform. Triggers include requests to create a custom component (decorated with @component), a custom tool (decorated with @tool), or to check custom code against the platform's structural constraints (single class/function per file, required decorators, type annotations, allowed dependencies).
---

# Haystack Custom Code Generator

## Overview

Guide for producing Haystack custom components and custom tools that run on the deepset/Haystack enterprise platform. Depending on the request, the output is either a custom component or a custom tool. Both are single Python files that must follow strict structural rules enforced by the platform.

## Quick Start

### Custom Component

```python
from haystack import component

@component
class WelcomeTextGenerator:
    """
    A component generating personal welcome message and making it upper case
    """

    @component.output_types(welcome_text=str, note=str)
    def run(self, name: str):
        return {
            "welcome_text": f'Hello {name}, welcome to Haystack!'.upper(),
            "note": "welcome message is ready"
        }
```

### Custom Tool

```python
from haystack.tools import tool
from typing import Annotated, Literal

@tool
def get_weather(
    city: Annotated[str, "the city for which to get the weather"],
    unit: Annotated[Literal["Celsius", "Fahrenheit"], "the unit for the temperature"]
):
    return {
        "city": city,
        "temperature": "20 degrees " + ("Celsius" if unit == "Celsius" else "Fahrenheit")
    }
```

## Using Custom Code in Pipeline YAML

Custom components and custom tools are embedded in a pipeline YAML by wrapping the Python source (as a string) inside a deepset Cloud wrapper node:

- Custom Component → `deepset_cloud_custom_nodes.code.code_component.Code`
- Custom Tool → `deepset_cloud_custom_nodes.tools.code_tool.CodeTool`

### Custom Component in YAML

The wrapper's `code` init_parameter holds the component source. An optional `init_parameters` init_parameter (a dict) is forwarded to the wrapped component's own `__init__` — this is what lets you configure a component's `__init__` defaults (e.g. `shout` below) from the pipeline YAML instead of hardcoding them in the component's source. This is useful for sharing and using the component in multiple pipelines.

```yaml
components:
  greeter:
    type: deepset_cloud_custom_nodes.code.code_component.Code
    init_parameters:
      code: |
        from haystack import component

        @component
        class WelcomeTextGenerator:
            """
            A component generating personal welcome message and making it upper case
            """

            def __init__(self, shout: bool = True):
                self.shout = shout

            @component.output_types(welcome_text=str, note=str)
            def run(self, name: str):
                text = f'Hello {name}, welcome to Haystack!'
                return {
                    "welcome_text": text.upper() if self.shout else text,
                    "note": "welcome message is ready"
                }
      init_parameters:
        shout: false
```

Note the two `init_parameters` levels are different things: the outer one is the `Code` wrapper's own init_parameters (`code` and `init_parameters`); the inner one is a plain dict forwarded to `WelcomeTextGenerator.__init__` — here it overrides `shout` to `false`.

### Custom Tool in YAML

Tools are attached to an `Agent` component's `tools` init_parameter as a list. Each entry mirrors `Tool.to_dict()`: a `type` (the wrapper class) and a `data` dict holding the wrapper's own init parameters — `name`, `description`, and `code` for `CodeTool`.

```yaml
components:
  agent:
    type: haystack.components.agents.agent.Agent
    init_parameters:
      chat_generator: ...
      tools:
        - type: deepset_cloud_custom_nodes.tools.code_tool.CodeTool
          data:
            name: get_weather
            description: Get the current weather for a city
            code: |
              from haystack.tools import tool
              from typing import Annotated, Literal

              @tool
              def get_weather(
                  city: Annotated[str, "the city for which to get the weather"],
                  unit: Annotated[Literal["Celsius", "Fahrenheit"], "the unit for the temperature"]
              ):
                  return {
                      "city": city,
                      "temperature": "20 degrees " + ("Celsius" if unit == "Celsius" else "Fahrenheit")
                  }
```

## Rules — Custom Components

- The resulting code must contain exactly one component class.
- The component class must have Haystack's `@component` decorator.
- The component must implement the `run` method.
- The `run` method must have Haystack's `@component.output_types` decorator and define the output types of the component.
- The `run` method's params must have type annotations.
- The return value of the `run` method is a dictionary having the specified output types as content.
- An `__init__` method may be implemented, but all parameters must have a default value. Defaults can be overridden per pipeline via the `Code` wrapper's own `init_parameters` dict (see YAML section above).
- A `warm_up` method must be implemented whenever heavier initialization is needed, such as creating a remote client that establishes a network connection.
- Only synchronous execution is supported: the `Code` wrapper calls the component's `run` method directly. A `run_async` method, even if defined, is never invoked.

## Rules — Custom Tools

- The resulting code must contain exactly one tool function.
- The tool function must have Haystack's `@tool` decorator.
- The tool function must return a dictionary containing one or more outputs — returned objects are converted to string automatically.
- The tool function's params must have type annotations.
- The tool function's params must use `Annotated` to describe each parameter to the LLM.
- The tool function must be a regular synchronous function. `async def` tool functions are not supported by the `CodeTool` wrapper

## Rules — Shared

- If the `get_available_python_dependencies` tool is available, only packages available via the `get_available_python_dependencies` tool may be used. Other packages will not work.
- `httpx` is preferred over the `requests` library.
- Only a single file may be written. Helper classes and functions may be implemented in the same file as the component or tool.
- The component class / tool function must be defined directly in the submitted code, not merely imported — a class or function pulled in via `import` is ignored when the platform looks for the `@component`/`@tool` target, even if it's correctly decorated. Imported classes or functions can be used by wrapping or inheritance.
- Common Python coding best practices such as PEP 8 must be followed.
- Built-in type hints are preferred over typing aliases (e.g. `dict` over `typing.Dict`, `list` over `typing.List`).
- Parameterized generics are preferred over non-parameterized generics (e.g. `list[dict[str, str]]` over `list`).
