# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Tests that every registered MCP tool is covered by the generated documentation.

The Tool Reference page (``docs/reference/tool_reference.md``) renders the
``deepset_mcp.tools`` package with mkdocstrings. Only names exported from that
package are rendered, so a tool that is registered but not exported silently
disappears from the published docs.
"""

import inspect
import re
from pathlib import Path
from typing import Any

import pytest

import deepset_mcp.tools as tools_package
from deepset_mcp.config import DOCS_SEARCH_TOOL_NAME
from deepset_mcp.mcp.tool_models import DeepsetDocsConfig
from deepset_mcp.mcp.tool_registry import TOOL_REGISTRY

# `search_docs` is registered through the `get_docs_search_tool` factory in the registry,
# but the underlying `deepset_mcp.tools.doc_search.search_docs` is what gets documented.
REGISTRY_NAME_TO_DOCUMENTED_NAME = {DOCS_SEARCH_TOOL_NAME: "search_docs"}

# Parameters injected by the tool factory rather than supplied by the caller.
INJECTED_PARAMS = {"client", "workspace", "ctx"}

TOOL_REFERENCE_DOC = Path(__file__).parents[2] / "docs" / "reference" / "tool_reference.md"


def _tool_names_listed_in_reference_doc() -> set[str]:
    """Extract the MCP tool names listed in the Tool Reference tables.

    The tables have the shape ``| `tool_name` | workspace | memory | description |``, so the tool
    name is the first cell of each row that starts with a backticked identifier.
    """
    names = set()
    for line in TOOL_REFERENCE_DOC.read_text().splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        # Only the inventory tables have 4 columns; the name-mismatch table has 2.
        if len(cells) != 4:
            continue
        match = re.fullmatch(r"`(\w+)`", cells[0])
        if match:
            names.add(match.group(1))
    return names


def _documented_name(tool_name: str, func: Any) -> str:
    """Resolve the name under which a registered tool is documented."""
    if tool_name in REGISTRY_NAME_TO_DOCUMENTED_NAME:
        return REGISTRY_NAME_TO_DOCUMENTED_NAME[tool_name]
    return str(getattr(func, "__name__", tool_name))


def _tool_function(tool_name: str, func: Any) -> Any:
    """Return the function whose docstring is exposed to the LLM.

    Some tools are built by factories that take a dependency and return the actual tool,
    so it is the inner function that carries the tool documentation.
    """
    if tool_name.endswith("object_store"):
        explorer = object()  # only closed over, never called during introspection
        return func(explorer)
    if tool_name == DOCS_SEARCH_TOOL_NAME:
        return func(DeepsetDocsConfig(pipeline_name="docs", api_key="key", workspace_name="docs"))
    return func


@pytest.mark.parametrize("tool_name", sorted(TOOL_REGISTRY))
def test_registered_tool_is_exported_for_docs(tool_name: str) -> None:
    """Every registered tool must be exported from `deepset_mcp.tools` to appear in the docs."""
    func, _ = TOOL_REGISTRY[tool_name]
    name = _documented_name(tool_name, func)

    assert name in tools_package.__all__, (
        f"MCP tool '{tool_name}' resolves to '{name}', which is not in "
        f"deepset_mcp.tools.__all__, so it is missing from the Tool Reference docs."
    )
    assert hasattr(tools_package, name), f"'{name}' is listed in __all__ but not importable from deepset_mcp.tools"


def test_tool_reference_doc_lists_every_registered_tool() -> None:
    """The Tool Reference tables must list every registered MCP tool, by its MCP tool name."""
    listed = _tool_names_listed_in_reference_doc()
    registered = set(TOOL_REGISTRY)

    missing = registered - listed
    assert not missing, (
        f"{TOOL_REFERENCE_DOC.name} does not list these registered MCP tools: {sorted(missing)}. "
        f"Add them to the appropriate table."
    )

    stale = listed - registered
    assert not stale, (
        f"{TOOL_REFERENCE_DOC.name} lists tools that are not in TOOL_REGISTRY: {sorted(stale)}. "
        f"Remove them or correct the names."
    )


def test_tools_all_is_consistent() -> None:
    """`__all__` must only list names the package actually exports."""
    for name in tools_package.__all__:
        assert hasattr(tools_package, name), f"deepset_mcp.tools.__all__ lists '{name}', which does not exist"


@pytest.mark.parametrize("tool_name", sorted(TOOL_REGISTRY))
def test_registered_tool_has_documented_signature(tool_name: str) -> None:
    """Every tool needs a docstring documenting each caller-supplied parameter and its return value."""
    func, config = TOOL_REGISTRY[tool_name]
    target = _tool_function(tool_name, func)

    doc = inspect.getdoc(target)
    assert doc, f"MCP tool '{tool_name}' has no docstring; the docstring is its description for the LLM."
    assert doc.strip().splitlines()[0].strip(), f"MCP tool '{tool_name}' has no summary line in its docstring."

    documented = set(re.findall(r":param\s+(\w+)\s*:", doc))
    expected = {
        param
        for param in inspect.signature(target).parameters
        if param not in INJECTED_PARAMS and param not in (config.custom_args or {}) and not param.startswith("_")
    }
    missing = expected - documented
    assert not missing, f"MCP tool '{tool_name}' is missing ':param:' documentation for: {sorted(missing)}"

    assert re.search(r":returns?\s*:", doc), f"MCP tool '{tool_name}' does not document its return value."
