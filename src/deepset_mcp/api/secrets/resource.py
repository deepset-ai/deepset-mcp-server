# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any

from deepset_mcp.api.exceptions import ResourceNotFoundError
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.api.secrets.models import Secret, SecretList
from deepset_mcp.api.secrets.protocols import SecretResourceProtocol
from deepset_mcp.api.shared_models import NoContentResponse
from deepset_mcp.api.transport import raise_for_status


class SecretResource(SecretResourceProtocol):
    """Resource for managing secrets in deepset."""

    def __init__(self, client: AsyncClientProtocol) -> None:
        """Initialize a SecretResource.

        :param client: The API client to use for requests.
        """
        self._client = client

    async def list(
        self,
        limit: int = 10,
        field: str = "created_at",
        order: str = "DESC",
    ) -> SecretList:
        """List secrets with pagination.

        :param limit: Maximum number of secrets to return.
        :param field: Field to sort by.
        :param order: Sort order (ASC or DESC).

        :returns: List of secrets with pagination info.
        """
        params = {
            "limit": str(limit),
            "field": field,
            "order": order,
        }

        resp = await self._client.request(
            endpoint="v2/secrets",
            method="GET",
            response_type=dict[str, Any],
            params=params,
        )

        raise_for_status(resp)

        if resp.json is None:
            raise ResourceNotFoundError("Failed to retrieve secrets.")

        return SecretList(**resp.json)

    async def create(self, name: str, secret: str) -> NoContentResponse:
        """Create a new secret.

        :param name: The name of the secret.
        :param secret: The secret value.

        :returns: NoContentResponse indicating successful creation.
        """
        data = {
            "name": name,
            "secret": secret,
        }

        resp = await self._client.request(
            endpoint="v2/secrets",
            method="POST",
            data=data,
            response_type=None,
        )

        raise_for_status(resp)
        return NoContentResponse(message="Secret created successfully.")

    async def get(self, secret_id: str) -> Secret:
        """Get a specific secret by ID.

        :param secret_id: The ID of the secret to retrieve.

        :returns: Secret information.
        """
        resp = await self._client.request(
            endpoint=f"v2/secrets/{secret_id}",
            method="GET",
            response_type=dict[str, Any],
        )

        raise_for_status(resp)

        if resp.json is None:
            raise ResourceNotFoundError(f"Secret '{secret_id}' not found.")

        return Secret(**resp.json)

    async def delete(self, secret_id: str) -> NoContentResponse:
        """Delete a secret by ID.

        :param secret_id: The ID of the secret to delete.

        :returns: NoContentResponse indicating successful deletion.
        """
        resp = await self._client.request(
            endpoint=f"v2/secrets/{secret_id}",
            method="DELETE",
            response_type=None,
        )

        raise_for_status(resp)
        return NoContentResponse(message="Secret deleted successfully.")
