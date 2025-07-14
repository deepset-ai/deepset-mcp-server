# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any

from deepset_mcp.api.exceptions import ResourceNotFoundError
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.api.shared_models import DeepsetUser
from deepset_mcp.api.transport import raise_for_status
from deepset_mcp.api.user.protocols import UserResourceProtocol


class UserResource(UserResourceProtocol):
    """Resource for managing users in deepset."""

    def __init__(self, client: AsyncClientProtocol) -> None:
        """Initialize a UserResource.

        :param client: The API client to use for requests.
        """
        self._client = client

    async def get(self, user_id: str) -> DeepsetUser:
        """Get user information by user ID.

        :param user_id: The ID of the user to fetch.

        :returns: User information.
        """
        resp = await self._client.request(
            endpoint=f"v1/users/{user_id}",
            method="GET",
            response_type=dict[str, Any],
        )

        raise_for_status(resp)

        if resp.json is None:
            raise ResourceNotFoundError(f"User '{user_id}' not found.")

        return DeepsetUser(**resp.json)
