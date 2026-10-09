# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Name to UUID lookups for the v2 routes, which are keyed by workspace and pipeline UUIDs."""

import asyncio
from typing import TYPE_CHECKING

from deepset_mcp.api.exceptions import UnexpectedAPIError
from deepset_mcp.api.transport import raise_for_status

if TYPE_CHECKING:
    from deepset_mcp.api.protocols import AsyncClientProtocol


async def workspace_id(client: "AsyncClientProtocol", workspace: str) -> str:
    """Resolve a workspace name to its UUID."""
    return str((await client.workspaces().get(workspace)).workspace_id)


async def pipeline_id(client: "AsyncClientProtocol", workspace: str, pipeline_name: str) -> str:
    """Resolve a pipeline name to its UUID."""
    return (await client.pipelines(workspace).get(pipeline_name)).id


async def workspace_and_pipeline_ids(
    client: "AsyncClientProtocol", workspace: str, pipeline_name: str
) -> tuple[str, str]:
    """Resolve both UUIDs concurrently."""
    return await asyncio.gather(workspace_id(client, workspace), pipeline_id(client, workspace, pipeline_name))


async def organization_id(client: "AsyncClientProtocol") -> str:
    """Resolve the organization UUID of the API key's user."""
    resp = await client.request(endpoint="v1/me", method="GET")
    raise_for_status(resp)
    try:
        return str(resp.json["organization"]["organization_id"])  # type: ignore[index]
    except (KeyError, TypeError) as e:
        raise UnexpectedAPIError(
            status_code=resp.status_code, message="No organization in /v1/me response", detail=None
        ) from e
