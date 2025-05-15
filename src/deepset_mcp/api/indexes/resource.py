from typing import Optional

from deepset_mcp.api.clients import AsyncRestClient
from deepset_mcp.api.indexes.models import Index, IndexList


class IndexResource:
    """Resource for interacting with deepset indexes."""

    def __init__(self, client: AsyncRestClient, workspace: str) -> None:
        """Initialize the index resource.

        :param client: The async REST client.
        :param workspace: The workspace to use.
        """
        self._client = client
        self._workspace = workspace

    async def list(self, limit: Optional[int] = None, page_number: Optional[int] = None) -> IndexList:
        """List all indexes.

        :param limit: Maximum number of indexes to return.
        :param page_number: Page number for pagination.

        :returns: List of indexes.
        """
        params = {}
        if limit is not None:
            params["limit"] = limit
        if page_number is not None:
            params["page_number"] = page_number

        response = await self._client.get(
            f"/api/v1/workspaces/{self._workspace}/indexes", params=params
        )
        return IndexList.model_validate(response)

    async def get(self, name: str) -> Index:
        """Get a specific index.

        :param name: Name of the index.

        :returns: Index details.
        """
        response = await self._client.get(
            f"/api/v1/workspaces/{self._workspace}/indexes/{name}"
        )
        return Index.model_validate(response)