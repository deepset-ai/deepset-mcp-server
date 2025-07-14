# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any

from deepset_mcp.api.exceptions import ResourceNotFoundError
from deepset_mcp.api.haystack_service.protocols import HaystackServiceProtocol
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.api.transport import raise_for_status


class HaystackServiceResource(HaystackServiceProtocol):
    """Manages interactions with the deepset Haystack service API."""

    def __init__(self, client: AsyncClientProtocol) -> None:
        """Initializes a HaystackServiceResource instance."""
        self._client = client

    async def get_component_schemas(self) -> dict[str, Any]:
        """Fetch the component schema from the API.

        Returns:
            The component schema as a dictionary
        """
        resp = await self._client.request(
            endpoint="v1/haystack/components",
            method="GET",
            headers={"accept": "application/json"},
            data={"domain": "deepset-cloud"},
        )

        raise_for_status(resp)

        return resp.json if resp.json is not None else {}

    async def get_component_input_output(self, component_name: str) -> dict[str, Any]:
        """Fetch the component input and output schema from the API.

        Args:
            component_name: The name of the component to fetch the input/output schema for

        Returns:
            The component input/output schema as a dictionary
        """
        resp = await self._client.request(
            endpoint="v1/haystack/components/input-output",
            method="GET",
            headers={"accept": "application/json"},
            params={"domain": "deepset-cloud", "names": component_name},
            response_type=list[dict[str, Any]],
        )

        raise_for_status(resp)

        if resp.json is None or len(resp.json) == 0:
            raise ResourceNotFoundError(f"Component '{component_name}' not found.")

        return resp.json[0] if resp.json is not None else {}
