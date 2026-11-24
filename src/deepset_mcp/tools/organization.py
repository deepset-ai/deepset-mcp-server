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
    organization. Without it, the default organization is used.
    Only works when connected through OAuth: API keys are bound to a single organization, so there is nothing
    to choose.

    :param client: The async client for API communication.
    :returns: List of organizations with 'organization_id' and 'name', or error message.
    """
    resp = await client.request("/v2/organizations")
    if not resp.success:
        if resp.status_code == 401:
            return (
                "Failed to list organizations (HTTP 401). Organization selection requires OAuth. "
                "API keys are tied to one organization, so omit 'organization_id' when calling tools. "
                "Otherwise, your credentials may have expired."
            )
        return f"Failed to list organizations (HTTP {resp.status_code}): {resp.text}"
    return list((resp.json or {}).get("organizations", []))
