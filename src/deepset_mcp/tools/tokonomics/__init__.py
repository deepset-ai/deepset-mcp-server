# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""
Tokonomics: Explorable and Referenceable Tools for LLM Agents.

=============================================================

A library that provides token-efficient object exploration and reference
passing capabilities for LLM agents.

Key Features:
- TTL-based object storage for temporary results
- Rich object exploration with multiple rendering modes
- Reference-based parameter passing (@obj_001.path.to.value)
- Type-safe decorators that preserve function signatures
- Configurable preview truncation and custom rendering callbacks

Usage:
------

Basic explorable tool:

    >>> from deepset_mcp.tools.tokonomics import explorable
    >>>
    >>> @explorable
    >>> def get_data():
    ...     return {"users": [{"name": "Alice", "age": 30}]}
    >>>
    >>> result = get_data()
    >>> print(result)  # Shows rich preview
    >>> result.obj_id  # "obj_001"
    >>> result.value   # Original data

Referenceable tool that accepts references:

    >>> from deepset_mcp.tools.tokonomics import referenceable
    >>>
    >>> @referenceable
    >>> def process_users(users: list) -> str:
    ...     return f"Processed {len(users)} users"
    >>>
    >>> # Use with direct data
    >>> process_users([{"name": "Bob"}])
    >>>
    >>> # Use with reference
    >>> process_users("@obj_001.users")

Exploration utilities:

    >>> from deepset_mcp.tools.tokonomics import explore, search
    >>>
    >>> # Explore object structure
    >>> explore("obj_001", mode="tree")
    >>>
    >>> # Search within objects
    >>> search("obj_001", "Alice")
"""

from .decorators import explorable, explorable_and_referenceable, referenceable
from .explorer import RichExplorer
from .object_store import Explorable, ObjectRef, ObjectStore

__all__ = [
    # Core classes
    "Explorable",
    "ObjectRef",
    "ObjectStore",
    "RichExplorer",
    # Decorators
    "explorable",
    "referenceable",
    "explorable_and_referenceable",
]

__version__ = "0.1.0"
