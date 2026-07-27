---
name: custom-code
description: Use this skill whenever writing, generating, reviewing, or fixing a Haystack custom component or custom tool for the deepset/Haystack enterprise platform. Triggers include requests to create a custom component (decorated with @component), a custom tool (decorated with @tool), or to check custom code against the platform's structural constraints (single class/function per file, required decorators, type annotations, allowed dependencies).
---

# Haystack Custom Code Generator

## Overview

Guide for producing Haystack custom components and custom tools that run on the deepset/Haystack enterprise platform. Depending on the request, the output is either a custom component or a custom tool. Both are single Python files that must follow strict structural rules enforced by the platform.

## Quick Start

Custom components and custom tools are embedded differently in a pipeline's YAML:

- A **custom component** is declared as a standalone pipeline component with a fixed `type` and an `init_parameters.code` field holding the Python source as a block scalar.
- A **custom tool** is not a standalone pipeline component. It is listed under the `tools` init parameter of a tool-using component (e.g. `haystack.components.agents.agent.Agent`), with a fixed `type` and a `data.code` field (alongside `data.name`/`data.description` and a sibling `_meta` block) holding the Python source.

In both cases the `type` never changes — only the `code` changes based on what is being built.

### Custom Component

`type`: `deepset_cloud_custom_nodes.code.code_component.Code`

Python source:

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

Pipeline YAML:

```yaml
components:
  welcome_text_generator:
    type: deepset_cloud_custom_nodes.code.code_component.Code
    init_parameters:
      code: |
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

`type`: `deepset_cloud_custom_nodes.tools.code_tool.CodeTool`

Python source:

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

Pipeline YAML (nested inside an `Agent`'s `tools` list):

```yaml
components:
  agent:
    type: haystack.components.agents.agent.Agent
    init_parameters:
      # ... other Agent init_parameters (chat_generator, system_prompt, etc.)
      tools:
      - type: deepset_cloud_custom_nodes.tools.code_tool.CodeTool
        data:
          name: get_weather
          description:
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
        _meta:
          name: get_weather
          description:
          tool_id:
```

> Platform-exported YAML often uses a folded block scalar (`code: >`) instead of `|`. Folded style joins single line breaks into spaces but preserves breaks around more-indented lines — so a blank line must separate every top-level statement (imports, decorators, `def`) to keep it on its own line, while nested/indented code inside a function body needs no extra blank lines. Using `|` (literal style), as above, avoids this pitfall entirely and is safe when authoring this YAML by hand.

## Rules — Custom Components

- The resulting code must contain exactly one component class.
- The component class must have Haystack's `@component` decorator.
- The component must implement the `run` method.
- The `run` method must have Haystack's `@component.output_types` decorator and define the output types of the component.
- The `run` method's params must have type annotations.
- The return value of the `run` method is a dictionary having the specified output types as content.
- An `__init__` method may be implemented, but it must not accept any parameters.
- A `warm_up` method must be implemented whenever heavier initialization is needed, such as creating a remote client that establishes a network connection.

## Rules — Custom Tools

- The resulting code must contain exactly one tool function.
- The tool function must have Haystack's `@tool` decorator.
- The tool function must return a dictionary containing one or more outputs — returned objects are converted to string automatically.
- The tool function's params must have type annotations.
- The tool function's params must use `Annotated` to describe each parameter to the LLM.

## Rules — Shared

- Only packages available via the `get_available_python_dependencies` tool may be used. Other packages will not work.
- `httpx` is preferred over the `requests` library.
- Only a single file may be written. Helper classes and functions may be implemented in the same file as the component or tool.
- Common Python coding best practices such as PEP 8 must be followed.
- Built-in type hints are preferred over typing aliases (e.g. `dict` over `typing.Dict`, `list` over `typing.List`).
- Parameterized generics are preferred over non-parameterized generics (e.g. `list[dict[str, str]]` over `list`).
