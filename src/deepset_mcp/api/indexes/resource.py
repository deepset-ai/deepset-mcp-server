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

    async def create(self, name: str, config_yaml: str, description: str | None = None) -> Index:
        """Create a new index with the given name and configuration.

        :param name: Name of the index
        :param config_yaml: YAML configuration for the index
        :param description: Optional description for the index
        :returns: Created index details
        """
        data = {
            "name": name,
            "config_yaml": config_yaml,
        }
        if description is not None:
            data["description"] = description

        response = await self._client.request(
            f"/api/v1/workspaces/{self._workspace}/indexes",
            method="POST",
            data=data
        )

        raise_for_status(response)

        return Index.model_validate(response.json)

    async def update(
        self,
        index_name: str,
        updated_index_name: str | None = None,
        config_yaml: str | None = None
    ) -> Index:
        """Update name and/or configuration of an existing index.

        :param index_name: Name of the index to update
        :param updated_index_name: Optional new name for the index
        :param config_yaml: Optional new YAML configuration
        :returns: Updated index details
        """
        data = {}
        if updated_index_name is not None:
            data["name"] = updated_index_name
        if config_yaml is not None:
            data["config_yaml"] = config_yaml

        if not data:
            raise ValueError("At least one of updated_index_name or config_yaml must be provided")

        response = await self._client.request(
            f"/api/v1/workspaces/{self._workspace}/indexes/{index_name}",
            method="PATCH",
            data=data
        )

        raise_for_status(response)

        return Index.model_validate(response.json)
