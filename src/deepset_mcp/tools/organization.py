# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Tools for interacting with organizations."""

from typing import Any

from deepset_mcp.api.protocols import AsyncClientProtocol


async def list_organizations(*, client: AsyncClientProtocol) -> list[dict[str, Any]] | str:
    """Lists the organizations the user belongs to.

    Use this when the user belongs to several organizations and wants to work in a specific one.
    Pass the returned 'organization_id' as the 'organization_id' argument of other tools to run them in that
    organization. Without it, the default organization is used. Only works when connected through OAuth.

    :param client: The async client for API communication.
    :returns: List of organizations with 'organization_id' and 'name', or error message.
    """
    resp = await client.request("/v2/organizations")
    if not resp.success:
        return f"Failed to list organizations (HTTP {resp.status_code}): {resp.text}"
    return list((resp.json or {}).get("organizations", []))
