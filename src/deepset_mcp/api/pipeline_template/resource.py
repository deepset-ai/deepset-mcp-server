# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any

from deepset_mcp.api.exceptions import UnexpectedAPIError
from deepset_mcp.api.pipeline_template.models import PipelineTemplate
from deepset_mcp.api.pipeline_template.protocols import PipelineTemplateResourceProtocol
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.api.shared_models import PaginatedResponse
from deepset_mcp.api.transport import raise_for_status


class PipelineTemplateResource(PipelineTemplateResourceProtocol):
    """Resource for interacting with pipeline templates in a workspace."""

    def __init__(self, client: AsyncClientProtocol, workspace: str) -> None:
        """Initialize the pipeline template resource.

        Parameters
        ----------
        client : AsyncClientProtocol
            Client to use for making API requests
        workspace : str
            Workspace to operate in
        """
        self._client = client
        self._workspace = workspace

    async def get_template(self, template_name: str) -> PipelineTemplate:
        """Fetch a single pipeline template by its name.

        Parameters
        ----------
        template_name : str
            Name of the template to fetch

        Returns
        -------
        PipelineTemplate
            The requested pipeline template
        """
        response = await self._client.request(f"/v1/workspaces/{self._workspace}/pipeline_templates/{template_name}")
        raise_for_status(response)
        data = response.json

        return PipelineTemplate.model_validate(data)

    async def list(
        self,
        limit: int = 10,
        after: str | None = None,
        field: str = "created_at",
        order: str = "DESC",
        filter: str | None = None,
    ) -> PaginatedResponse[PipelineTemplate]:
        """Lists pipeline templates and returns the first page of results.

        The returned object can be iterated over to fetch subsequent pages.

        :param limit: The maximum number of pipeline templates to return per page.
        :param after: The cursor to fetch the next page of results.
        :param field: Field to sort by (default: "created_at").
        :param order: Sort order, either "ASC" or "DESC" (default: "DESC").
        :param filter: OData filter expression for filtering templates.
        :returns: A `PaginatedResponse` object containing the first page of pipeline templates.
        """
        # TODO: Remove when fixed
        if after is not None:
            raise ValueError("Pagination using 'after' parameter is currently not supported by the deepset platform.")

        # 1. Prepare arguments for the initial API call
        # TODO: Pagination in the deepset API is currently implemented in an unintuitive way.
        # TODO: The cursor is always time based (created_at) and after signifies templates older than the current cursor
        # TODO: while 'before' signals templates younger than the current cursor.
        # TODO: This is applied irrespective of any sort (e.g. name) that would conflict with this approach.
        # TODO: Change this to 'after' once the behaviour is fixed on the deepset API
        request_params = {"limit": limit, "before": after, "field": field, "order": order}
        if filter is not None:
            request_params["filter"] = filter
        request_params = {k: v for k, v in request_params.items() if v is not None}

        # 2. Make the first API call using a private, stateless method
        page = await self._list_api_call(**request_params)

        # 3. Inject the logic needed for subsequent fetches into the response object
        page._inject_paginator(
            fetch_func=self._list_api_call,
            # Base args for the *next* fetch don't include initial cursors
            base_args={"limit": limit, "field": field, "order": order, "filter": filter},
        )
        return page

    async def _list_api_call(self, **kwargs: Any) -> PaginatedResponse[PipelineTemplate]:
        """A private, stateless method that performs the raw API call."""
        resp = await self._client.request(
            endpoint=f"v1/workspaces/{self._workspace}/pipeline_templates", method="GET", params=kwargs
        )
        raise_for_status(resp)
        if resp.json is None:
            raise UnexpectedAPIError(status_code=resp.status_code, message="Empty response", detail=None)

        return PaginatedResponse[PipelineTemplate].create_with_cursor_field(resp.json, "name")
