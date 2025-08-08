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

    async def run_component(
        self,
        component_type: str,
        init_params: dict[str, Any] | None = None,
        input_data: dict[str, Any] | None = None,
        input_types: dict[str, str] | None = None,
        workspace: str | None = None,
    ) -> dict[str, Any]:
        """Run a Haystack component with the given parameters.

        :param component_type: The type of component to run (e.g., "haystack.components.builders.PromptBuilder")
        :param init_params: Initialization parameters for the component
        :param input_data: Input data for the component
        :param input_types: Optional type information for inputs (inferred if not provided)
        :param workspace: Optional workspace name to run the component in

        :returns: Dictionary containing the component's output sockets
        """
        payload: dict[str, Any] = {
            "component_type": component_type,
            "init_params": init_params or {},
            "input": input_data or {},
        }

        if input_types is not None:
            payload["input_types"] = input_types

        endpoint = "v1/haystack/components/run"
        if workspace is not None:
            endpoint = f"v1/workspaces/{workspace}/haystack/components/run"

        resp = await self._client.request(
            endpoint=endpoint,
            method="POST",
            headers={
                "accept": "application/json",
                "content-type": "application/json",
            },
            data=payload,
            response_type=dict[str, Any],
        )

        raise_for_status(resp)

        return resp.json if resp.json is not None else {}
