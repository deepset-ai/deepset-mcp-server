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

from .explorer import RichExplorer
from .object_store import Explorable, ObjectRef, ObjectStore

F = TypeVar("F", bound=Callable[..., Any])


def _is_reference(value: Any) -> bool:
    """Check if a value is a reference string."""
    return isinstance(value, str) and ObjectRef.parse(value) is not None


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


def _enhance_docstring_for_references(original: str, param_info: dict[str, dict[str, Any]], func_name: str) -> str:
    """Add reference documentation to function docstring.

    :param original: Original docstring.
    :param param_info: Parameter modification info.
    :param func_name: Function name for examples.
    :return: Enhanced docstring.
    """
    if not original:
        original = f"{func_name} function with reference support."

    # Build the reference section
    ref_section = [
        "",
        "**Reference Support**",
        "",
        "All parameters accept object references in the form ``@obj_id`` or ``@obj_id.path.to.value``.",
        "",
    ]

    if param_info:
        ref_section.append("Parameter types after decoration:")
        ref_section.append("")
        for name, info in param_info.items():
            if info["accepts_str"]:
                ref_section.append(f"- ``{name}``: {info['original']} (already accepts strings)")
            else:
                ref_section.append(f"- ``{name}``: {info['original']} → {info['modified']} (now accepts references)")
        ref_section.append("")

    ref_section.extend(
        [
            "Examples::",
            "",
            "    # Direct call with values",
            f"    {func_name}(data={{'key': 'value'}}, threshold=10)",
            "",
            "    # Call with references",
            f"    {func_name}(data='@obj_001', threshold='@obj_002.config.threshold')",
            "",
            "    # Mixed call",
            f"    {func_name}(data='@obj_001.items', threshold=10)",
        ]
    )

    return original.rstrip() + "\n" + "\n".join(ref_section)


def _enhance_docstring_for_explorable(original: str, func_name: str) -> str:
    """Add explorable documentation to function docstring.

    :param original: Original docstring.
    :param func_name: Function name.
    :return: Enhanced docstring.
    """
    if not original:
        original = f"{func_name} function with stored output."

    section = [
        "",
        "**Output Storage**",
        "",
        "The output of this function is automatically stored and can be referenced in other functions.",
        "The function returns a formatted preview of the result along with an object ID (e.g., ``@obj_123``).",
        "",
        "Use the returned object ID to pass this result to other functions that accept references.",
    ]

    return original.rstrip() + "\n" + "\n".join(section)


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
    >>> # result contains a preview and object ID like "@obj_001"
    """

    def decorator(func: F) -> F:
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Explorable[Any]:
                result = await func(*args, **kwargs)
                obj_id = object_store.put(result)
                preview = explorer.explore(obj_id)
                return Explorable(obj_id, result, preview)

            # Enhance docstring
            async_wrapper.__doc__ = _enhance_docstring_for_explorable(func.__doc__ or "", func.__name__)
            return async_wrapper  # type: ignore[return-value]
        else:

            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Explorable[Any]:
                result = func(*args, **kwargs)
                obj_id = object_store.put(result)
                preview = explorer.explore(obj_id)
                return Explorable(obj_id, result, preview)

            # Enhance docstring
            sync_wrapper.__doc__ = _enhance_docstring_for_explorable(func.__doc__ or "", func.__name__)
            return sync_wrapper  # type: ignore[return-value]

    return decorator


def referenceable(
    *,
    object_store: ObjectStore,
    explorer: RichExplorer,
) -> Callable[[F], F]:
    """Decorator factory that enables parameters to accept object references.

    Parameters can accept reference strings like '@obj_001' or '@obj_001.path.to.value'
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
    >>> process_data("@obj_001", "@obj_002.config.threshold")
    """

    def resolve_reference(ref_str: str) -> Any:
        """Resolve a reference string to its actual value."""
        ref = ObjectRef.parse(ref_str)
        if ref is None:
            raise ValueError(f"Invalid reference format: {ref_str}")

        obj = object_store.get(ref.obj_id)
        if obj is None:
            raise ValueError(f"Object @{ref.obj_id} not found or expired")

        if ref.path:
            try:
                explorer._validate_path(ref.path)
                return glom(obj, explorer._parse_path(ref.path))
            except GlomError as exc:
                raise ValueError(f"Navigation error at {ref.path}: {exc}") from exc
            except ValueError as exc:
                raise ValueError(f"Invalid path {ref.path}: {exc}") from exc

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
            async_wrapper.__doc__ = _enhance_docstring_for_references(func.__doc__ or "", param_info, func.__name__)
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
            sync_wrapper.__doc__ = _enhance_docstring_for_references(func.__doc__ or "", param_info, func.__name__)
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
    >>> result = merge_data("@obj_001", {"new": "data"})
    >>> # result contains a preview and can be referenced as "@obj_002"
    """

    def decorator(func: F) -> F:
        # First apply referenceable to handle input references
        ref_func = referenceable(object_store=object_store, explorer=explorer)(func)
        # Then apply explorable to handle output storage
        exp_func = explorable(object_store=object_store, explorer=explorer)(ref_func)

        # Combine docstrings (remove duplicate function name line)
        if ref_func.__doc__ and exp_func.__doc__:
            # Take the reference part from ref_func and explorable part from exp_func
            ref_lines = ref_func.__doc__.split("\n")
            exp_lines = exp_func.__doc__.split("\n")

            # Find where the reference section starts
            ref_start = next((i for i, line in enumerate(ref_lines) if "**Reference Support**" in line), len(ref_lines))
            # Find where the explorable section starts
            exp_start = next((i for i, line in enumerate(exp_lines) if "**Output Storage**" in line), 0)

            # Combine: original + reference section + explorable section
            # Take everything from ref_func including reference section but excluding examples
            # Find end of reference section (before examples)
            ref_end = len(ref_lines)
            for i in range(ref_start, len(ref_lines)):
                if "Examples::" in ref_lines[i]:
                    ref_end = i
                    break

            combined = ref_lines[:ref_end] + exp_lines[exp_start:]
            exp_func.__doc__ = "\n".join(combined)

        return exp_func

    return decorator
