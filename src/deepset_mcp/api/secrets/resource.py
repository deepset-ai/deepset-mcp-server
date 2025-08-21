# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any

from deepset_mcp.api.exceptions import ResourceNotFoundError
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.api.secrets.models import Secret
from deepset_mcp.api.secrets.protocols import SecretResourceProtocol
from deepset_mcp.api.shared_models import NoContentResponse, PaginatedResponse
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
        after: str | None = None,
    ) -> PaginatedResponse[Secret]:
        """List secrets with pagination.

        The returned object can be iterated over to fetch subsequent pages.

        :param limit: Maximum number of secrets to return.
        :param field: Field to sort by.
        :param order: Sort order (ASC or DESC).
        :param after: The cursor to fetch the next page of results.

        :returns: A `PaginatedResponse` object containing the first page of secrets.
        """
        # 1. Prepare arguments for the initial API call
        # TODO: Pagination in the deepset API is currently implemented in an unintuitive way.
        # TODO: The cursor is always time based (created_at) and after signifies secrets older than the current cursor
        # TODO: while 'before' signals secrets younger than the current cursor.
        # TODO: This is applied irrespective of any sort (e.g. name) that would conflict with this approach.
        # TODO: Change this to 'after' once the behaviour is fixed on the deepset API
        request_params = {
            "limit": str(limit),
            "field": field,
            "order": order,
            "before": after,
        }
        request_params = {k: v for k, v in request_params.items() if v is not None}

        # 2. Make the first API call using a private, stateless method
        page = await self._list_api_call(**request_params)

        # 3. Inject the logic needed for subsequent fetches into the response object
        page._inject_paginator(
            fetch_func=self._list_api_call,
            # Base args for the *next* fetch don't include initial cursors
            base_args={"limit": str(limit), "field": field, "order": order},
        )
        return page

    async def _list_api_call(self, **kwargs: Any) -> PaginatedResponse[Secret]:
        """A private, stateless method that performs the raw API call."""
        resp = await self._client.request(
            endpoint="v2/secrets",
            method="GET",
            response_type=dict[str, Any],
            params=kwargs,
        )

        raise_for_status(resp)

        if resp.json is None:
            raise ResourceNotFoundError("Failed to retrieve secrets.")

        return PaginatedResponse[Secret].create_with_cursor_field(resp.json, "secret_id")

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
