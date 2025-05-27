from typing import Any

from deepset_mcp.api.custom_components.models import CustomComponentInstallationList, User
from deepset_mcp.api.exceptions import ResourceNotFoundError
from deepset_mcp.api.protocols import AsyncClientProtocol, CustomComponentsProtocol
from deepset_mcp.api.transport import raise_for_status


class CustomComponentsResource(CustomComponentsProtocol):
    """Resource for managing custom components in deepset."""

    def __init__(self, client: AsyncClientProtocol, workspace: str) -> None:
        """Initialize a CustomComponentsResource.
        
        :param client: The API client to use for requests.
        :param workspace: The workspace to operate in.
        """
        self._client = client
        self._workspace = workspace

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
            response_type=CustomComponentInstallationList,
        )

        raise_for_status(resp)

        if resp.json is None:
            return CustomComponentInstallationList(data=[], total=0, has_more=False)

        return resp.json

    async def get_latest_installation_logs(self) -> Any:
        """Get the logs from the latest custom component installation.
        
        :returns: Latest installation logs.
        """
        resp = await self._client.request(
            endpoint="v2/custom_components/logs",
            method="GET",
        )

        raise_for_status(resp)

        return resp.json if resp.json is not None else {}

    async def get_user(self, user_id: str) -> User:
        """Get user information by user ID.
        
        :param user_id: The ID of the user to fetch.
        
        :returns: User information.
        """
        resp = await self._client.request(
            endpoint=f"v1/users/{user_id}",
            method="GET",
            response_type=User,
        )

        raise_for_status(resp)

        if resp.json is None:
            raise ResourceNotFoundError(f"User '{user_id}' not found.")

        return resp.json
