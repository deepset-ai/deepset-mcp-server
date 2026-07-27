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
