# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any

from deepset_mcp.api.custom_components.models import CustomComponentInstallationList
from deepset_mcp.api.custom_components.protocols import CustomComponentsProtocol
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.api.transport import raise_for_status


class CustomComponentsResource(CustomComponentsProtocol):
    """Resource for managing custom components in deepset."""

    def __init__(self, client: AsyncClientProtocol) -> None:
        """Initialize a CustomComponentsResource.

        :param client: The API client to use for requests.
        """
        self._client = client

    async def list_installations(
        self, limit: int = 20, page_number: int = 1, field: str = "created_at", order: str = "DESC"
    ) -> CustomComponentInstallationList:
        """List custom component installations.

        :param limit: Maximum number of installations to return.
        :param page_number: Page number for pagination.
        :param field: Field to sort by.
        :param order: Sort order (ASC or DESC).

        :returns: List of custom component installations.
        """
        resp = await self._client.request(
            endpoint=f"v2/custom_components?limit={limit}&page_number={page_number}&field={field}&order={order}",
            method="GET",
            response_type=dict[str, Any],
        )

        raise_for_status(resp)

        if resp.json is None:
            return CustomComponentInstallationList(data=[], total=0, has_more=False)

        return CustomComponentInstallationList(**resp.json)

    async def get_latest_installation_logs(self) -> str | None:
        """Get the logs from the latest custom component installation.

        :returns: Latest installation logs.
        """
        resp = await self._client.request(
            endpoint="v2/custom_components/logs",
            method="GET",
        )

        raise_for_status(resp)

        return resp.text
