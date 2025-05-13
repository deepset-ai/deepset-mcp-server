from typing import Any

from deepset_mcp.api.protocols import AsyncClientProtocol, HaystackServiceProtocol
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
