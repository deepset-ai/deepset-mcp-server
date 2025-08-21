# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any
from urllib.parse import quote

from deepset_mcp.api.custom_components.models import CustomComponentInstallation
from deepset_mcp.api.custom_components.protocols import CustomComponentsProtocol
from deepset_mcp.api.exceptions import UnexpectedAPIError
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.api.shared_models import PaginatedResponse
from deepset_mcp.api.transport import raise_for_status


class CustomComponentsResource(CustomComponentsProtocol):
    """Resource for managing custom components in deepset."""

    def __init__(self, client: AsyncClientProtocol) -> None:
        """Initialize a CustomComponentsResource.

        :param client: The API client to use for requests.
        """
        self._client = client

    async def list_installations(
        self, limit: int = 20, after: str | None = None, field: str = "created_at", order: str = "DESC"
    ) -> PaginatedResponse[CustomComponentInstallation]:
        """Lists custom component installations and returns the first page of results.

        The returned object can be iterated over to fetch subsequent pages.

        :param limit: Maximum number of installations to return per page.
        :param after: The cursor to fetch the next page of results.
        :param field: Field to sort by.
        :param order: Sort order (ASC or DESC).
        :returns: A `PaginatedResponse` object containing the first page of installations.
        """
        # 1. Prepare arguments for the initial API call
        # TODO: Pagination in the deepset API is currently implemented in an unintuitive way.
        # TODO: The cursor is always time based (created_at) and after signifies installations older than the
        # TODO: current cursor
        # TODO: while 'before' signals installations younger than the current cursor.
        # TODO: This is applied irrespective of any sort (e.g. name) that would conflict with this approach.
        # TODO: Change this to 'after' once the behaviour is fixed on the deepset API
        request_params = {"limit": limit, "field": field, "order": order, "before": after}
        request_params = {k: v for k, v in request_params.items() if v is not None}

        # 2. Make the first API call using a private, stateless method
        page = await self._list_api_call(**request_params)

        # 3. Inject the logic needed for subsequent fetches into the response object
        page._inject_paginator(
            fetch_func=self._list_api_call,
            # Base args for the *next* fetch don't include initial cursors
            base_args={"limit": limit, "field": field, "order": order},
        )
        return page

    async def _list_api_call(self, **kwargs: Any) -> PaginatedResponse[CustomComponentInstallation]:
        """A private, stateless method that performs the raw API call."""
        params = "&".join([f"{key}={quote(str(value), safe='')}" for key, value in kwargs.items()])
        resp = await self._client.request(
            endpoint=f"v2/custom_components?{params}",
            method="GET",
            response_type=dict[str, Any],
        )
        raise_for_status(resp)
        if resp.json is None:
            raise UnexpectedAPIError(status_code=resp.status_code, message="Empty response", detail=None)

        return PaginatedResponse[CustomComponentInstallation].create_with_cursor_field(resp.json, "custom_component_id")

    async def get_latest_installation_logs(self) -> str | None:
        """Get the logs from the latest custom component installation.

        :returns: Latest installation logs.
        """
        resp = await self._client.request(
            endpoint="v2/custom_components/logs",
            method="GET",
        )

        raise_for_status(resp)

        return resp.text
