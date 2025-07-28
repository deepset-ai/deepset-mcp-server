# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""
Decorator factories for explorable and referenceable tools.

This module provides the @explorable and @referenceable decorators that enable
tools to store their outputs and accept reference inputs.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from functools import wraps
from types import UnionType
from typing import Any, TypeVar, Union, get_args, get_origin

from glom import GlomError, glom

from deepset_mcp.tools.tokonomics.explorer import RichExplorer
from deepset_mcp.tools.tokonomics.object_store import ObjectStore

F = TypeVar("F", bound=Callable[..., Any])


def _is_reference(value: Any) -> bool:
    """Check if a value is a reference string."""
    return isinstance(value, str) and value.startswith("@") and len(value) > 1


def _type_allows_str(annotation: Any) -> bool:
    """Check if a type annotation already allows string values."""
    if annotation is str:
        return True
    origin = get_origin(annotation)
    if origin in {Union, UnionType}:
        return str in get_args(annotation)
    return False


def _add_str_to_type(annotation: Any) -> Any:
    """Add str to a type annotation to allow reference strings."""
    if annotation is inspect.Parameter.empty:
        return str
    if _type_allows_str(annotation):
        return annotation
    return annotation | str


def _enhance_docstring_for_references(original: str, func_name: str) -> str:
    """Create complete docstring for LLM tool with reference support.

    :param original: Original docstring.
    :param func_name: Function name for examples.
    :return: Complete docstring for LLM tool.
    """
    if not original:
        original = f"{func_name} function."

    enhancement = [
        "",
        "All parameters accept object references in the form ``@obj_id`` or ``@obj_id.path.to.value``.",
        "",
        "Examples::",
        "",
        "    # Direct call with values",
        f"    {func_name}(data={{'key': 'value'}}, threshold=10)",
        "",
        "    # Call with references",
        f"    {func_name}(data='@obj_123', threshold='@obj_456.config.threshold')",
        "",
        "    # Mixed call",
        f"    {func_name}(data='@obj_123.items', threshold=10)",
    ]

    return original.rstrip() + "\n" + "\n".join(enhancement)


def _enhance_docstring_for_explorable(original: str, func_name: str) -> str:
    """Create complete docstring for LLM tool with output storage.

    :param original: Original docstring.
    :param func_name: Function name.
    :return: Complete docstring for LLM tool.
    """
    if not original:
        original = f"{func_name} function."

    enhancement = [
        "",
        "The output is automatically stored and can be referenced in other functions.",
        "Returns a formatted preview with an object ID (e.g., ``@obj_123``).",
        "Use the object store tools in combination with the object ID to view nested properties of the object.",
        "Use the returned object ID to pass this result to other functions.",
    ]

    return original.rstrip() + "\n" + "\n".join(enhancement)


def explorable(
    *,
    object_store: ObjectStore,
    explorer: RichExplorer,
) -> Callable[[F], F]:
    """Decorator factory that stores function results for later reference.

    :param object_store: The object store instance to use for storage.
    :param explorer: The RichExplorer instance to use for previews.
    :return: Decorator function.

    Examples
    --------
    >>> store = ObjectStore()
    >>> explorer = RichExplorer(store)
    >>>
    >>> @explorable(object_store=store, explorer=explorer)
    ... def process_data(data: dict) -> dict:
    ...     return {"processed": data}
    ...
    >>> result = process_data({"input": "value"})
    >>> # result contains a preview and object ID like "@obj_123"
    """

    def decorator(func: F) -> F:
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> str:
                result = await func(*args, **kwargs)
                obj_id = object_store.put(result)
                preview = explorer.explore(obj_id)

                return preview

            # Enhance docstring
            async_wrapper.__doc__ = _enhance_docstring_for_explorable(func.__doc__ or "", func.__name__)
            async_wrapper.__annotations__["return"] = str
            return async_wrapper  # type: ignore[return-value]
        else:

            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> str:
                result = func(*args, **kwargs)
                obj_id = object_store.put(result)
                preview = explorer.explore(obj_id)
                return preview

            # Enhance docstring
            sync_wrapper.__doc__ = _enhance_docstring_for_explorable(func.__doc__ or "", func.__name__)
            sync_wrapper.__annotations__["return"] = str
            return sync_wrapper  # type: ignore[return-value]

    return decorator


def referenceable(
    *,
    object_store: ObjectStore,
    explorer: RichExplorer,
) -> Callable[[F], F]:
    """Decorator factory that enables parameters to accept object references.

    Parameters can accept reference strings like '@obj_id' or '@obj_id.path.to.value'
    which are automatically resolved before calling the function.

    :param object_store: The object store instance to use for lookups.
    :param explorer: The RichExplorer instance to use for path validation.
    :return: Decorator function.

    Examples
    --------
    >>> store = ObjectStore()
    >>> explorer = RichExplorer(store)
    >>>
    >>> @referenceable(object_store=store, explorer=explorer)
    ... def process_data(data: dict, threshold: int) -> str:
    ...     return f"Processed {len(data)} items with threshold {threshold}"
    ...
    >>> # Call with actual values
    >>> process_data({"a": 1, "b": 2}, 10)
    >>>
    >>> # Call with references
    >>> process_data("@obj_123", "@obj_456.config.threshold")
    """

    def resolve_reference(ref_str: str) -> Any:
        """Resolve a reference string to its actual value."""
        obj_id, path = explorer.parse_reference(ref_str)

        obj = object_store.get(obj_id)
        if obj is None:
            raise ValueError(f"Object @{obj_id} not found or expired")

        if path:
            try:
                explorer._validate_path(path)
                return glom(obj, explorer._parse_path(path))
            except GlomError as exc:
                raise ValueError(f"Navigation error at {path}: {exc}") from exc
            except ValueError as exc:
                raise ValueError(f"Invalid path {path}: {exc}") from exc

        return obj

    def decorator(func: F) -> F:
        sig = inspect.signature(func)

        # Track which parameters need type modifications
        param_info: dict[str, dict[str, Any]] = {}
        new_params = []

        for name, param in sig.parameters.items():
            ann = param.annotation
            if ann is inspect.Parameter.empty:
                ann = Any

            if _type_allows_str(ann):
                # Already accepts strings
                param_info[name] = {"original": ann, "modified": ann, "accepts_str": True}
                new_params.append(param)
            else:
                # Add str to type union
                new_ann = _add_str_to_type(ann)
                param_info[name] = {"original": ann, "modified": new_ann, "accepts_str": False}
                new_params.append(param.replace(annotation=new_ann))

        new_sig = sig.replace(parameters=new_params)

        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                # Bind arguments to get parameter names
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()

                # Resolve references
                resolved_args = []
                resolved_kwargs = {}

                for name, value in bound.arguments.items():
                    info = param_info.get(name, {})

                    # Check for invalid string values
                    if not info.get("accepts_str", True) and isinstance(value, str):
                        if not _is_reference(value):
                            raise TypeError(
                                f"Parameter '{name}' expects {info['original']}, "
                                f"got string '{value}'. Use '@obj_id' for references."
                            )

                    # Resolve references
                    if _is_reference(value):
                        value = resolve_reference(value)

                    # Reconstruct args/kwargs
                    param = sig.parameters[name]
                    if param.kind in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD):
                        if name in list(sig.parameters)[: len(bound.args)]:
                            resolved_args.append(value)
                        else:
                            resolved_kwargs[name] = value
                    else:
                        resolved_kwargs[name] = value

                return await func(*resolved_args, **resolved_kwargs)

            # Update signature and docstring
            async_wrapper.__signature__ = new_sig  # type: ignore[attr-defined]
            async_wrapper.__doc__ = _enhance_docstring_for_references(func.__doc__ or "", func.__name__)
            return async_wrapper  # type: ignore[return-value]
        else:

            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                # Bind arguments to get parameter names
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()

                # Resolve references
                resolved_args = []
                resolved_kwargs = {}

                for name, value in bound.arguments.items():
                    info = param_info.get(name, {})

                    # Check for invalid string values
                    if not info.get("accepts_str", True) and isinstance(value, str):
                        if not _is_reference(value):
                            raise TypeError(
                                f"Parameter '{name}' expects {info['original']}, "
                                f"got string '{value}'. Use '@obj_id' for references."
                            )

                    # Resolve references
                    if _is_reference(value):
                        value = resolve_reference(value)

                    # Reconstruct args/kwargs
                    param = sig.parameters[name]
                    if param.kind in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD):
                        if name in list(sig.parameters)[: len(bound.args)]:
                            resolved_args.append(value)
                        else:
                            resolved_kwargs[name] = value
                    else:
                        resolved_kwargs[name] = value

                return func(*resolved_args, **resolved_kwargs)

            # Update signature and docstring
            sync_wrapper.__signature__ = new_sig  # type: ignore[attr-defined]
            sync_wrapper.__doc__ = _enhance_docstring_for_references(func.__doc__ or "", func.__name__)
            return sync_wrapper  # type: ignore[return-value]

    return decorator


def explorable_and_referenceable(
    *,
    object_store: ObjectStore,
    explorer: RichExplorer,
) -> Callable[[F], F]:
    """Decorator factory that combines @explorable and @referenceable functionality.

    The decorated function can accept reference parameters AND stores its result
    in the object store for later reference.

    :param object_store: The object store instance to use.
    :param explorer: The RichExplorer instance to use.
    :return: Decorator function.

    Examples
    --------
    >>> store = ObjectStore()
    >>> explorer = RichExplorer(store)
    >>>
    >>> @explorable_and_referenceable(object_store=store, explorer=explorer)
    ... def merge_data(data1: dict, data2: dict) -> dict:
    ...     return {**data1, **data2}
    ...
    >>> # Accepts references and returns preview with object ID
    >>> result = merge_data("@obj_123", {"new": "data"})
    >>> # result contains a preview and can be referenced as "@obj_002"
    """

    def decorator(func: F) -> F:
        # First apply referenceable to handle input references
        ref_func = referenceable(object_store=object_store, explorer=explorer)(func)
        # Then apply explorable to handle output storage
        exp_func = explorable(object_store=object_store, explorer=explorer)(ref_func)

        # Combine docstrings (remove duplicate function name line)
        if ref_func.__doc__ and exp_func.__doc__:
            exp_lines = exp_func.__doc__.split("\n")
            # Find where the explorable section starts
            exp_start = next(
                (
                    i
                    for i, line in enumerate(exp_lines)
                    if "The output is automatically stored and can be referenced" in line
                ),
                0,
            )

            combined = ref_func.__doc__ + "\n".join(exp_lines[exp_start:])
            exp_func.__doc__ = combined

        return exp_func

    return decorator
