from deepset_mcp.api.indexes.models import Index, IndexList
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.api.transport import raise_for_status


class IndexResource:
    """Resource for interacting with deepset indexes."""

    def __init__(self, client: AsyncClientProtocol, workspace: str) -> None:
        """Initialize the index resource.

        :param client: The async REST client.
        :param workspace: The workspace to use.
        """
        self._client = client
        self._workspace = workspace

    async def list(self, limit: int = 10, page_number: int = 1) -> IndexList:
        """List all indexes.

        :param limit: Maximum number of indexes to return.
        :param page_number: Page number for pagination.

        :returns: List of indexes.
        """
        params = {
            "limit": limit,
            "page_number": page_number,
        }

        response = await self._client.request(f"/api/v1/workspaces/{self._workspace}/indexes", params=params)

        raise_for_status(response)

        return IndexList.model_validate(response.json)

    async def get(self, index_name: str) -> Index:
        """Get a specific index.

        :param index_name: Name of the index.

        :returns: Index details.
        """
        response = await self._client.request(f"/api/v1/workspaces/{self._workspace}/indexes/{index_name}")

        raise_for_status(response)

        return Index.model_validate(response.json)
