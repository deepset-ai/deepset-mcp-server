# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any
from urllib.parse import quote

from deepset_mcp.api.exceptions import UnexpectedAPIError
from deepset_mcp.api.indexes.models import Index
from deepset_mcp.api.indexes.protocols import IndexResourceProtocol
from deepset_mcp.api.pipeline.models import PipelineValidationResult, ValidationError
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.api.shared_models import PaginatedResponse
from deepset_mcp.api.transport import raise_for_status


class IndexResource(IndexResourceProtocol):
    """Resource for interacting with deepset indexes."""

    def __init__(self, client: AsyncClientProtocol, workspace: str) -> None:
        """Initialize the index resource.

        :param client: The async REST client.
        :param workspace: The workspace to use.
        """
        self._client = client
        self._workspace = workspace

    async def list(self, limit: int = 10, after: str | None = None) -> PaginatedResponse[Index]:
        """Lists indexes and returns the first page of results.

        The returned object can be iterated over to fetch subsequent pages.

        :param limit: The maximum number of indexes to return per page.
        :param after: The cursor to fetch the next page of results.
        :returns: A `PaginatedResponse` object containing the first page of indexes.
        """
        # 1. Prepare arguments for the initial API call
        # TODO: Pagination in the deepset API is currently implemented in an unintuitive way.
        # TODO: The cursor is always time based (created_at) and after signifies indexes older than the current cursor
        # TODO: while 'before' signals indexes younger than the current cursor.
        # TODO: This is applied irrespective of any sort (e.g. name) that would conflict with this approach.
        # TODO: Change this to 'after' once the behaviour is fixed on the deepset API
        request_params = {"limit": limit, "before": after}
        request_params = {k: v for k, v in request_params.items() if v is not None}

        # 2. Make the first API call using a private, stateless method
        page = await self._list_api_call(**request_params)

        # 3. Inject the logic needed for subsequent fetches into the response object
        page._inject_paginator(
            fetch_func=self._list_api_call,
            # Base args for the *next* fetch don't include initial cursors
            base_args={"limit": limit},
        )
        return page

    async def _list_api_call(self, **kwargs: Any) -> PaginatedResponse[Index]:
        """A private, stateless method that performs the raw API call."""
        resp = await self._client.request(
            endpoint=f"v1/workspaces/{quote(self._workspace, safe='')}/indexes", method="GET", params=kwargs
        )
        raise_for_status(resp)
        if resp.json is None:
            raise UnexpectedAPIError(status_code=resp.status_code, message="Empty response", detail=None)

        return PaginatedResponse[Index].create_with_cursor_field(resp.json, "pipeline_index_id")

    async def get(self, index_name: str) -> Index:
        """Get a specific index.

        :param index_name: Name of the index.

        :returns: Index details.
        """
        response = await self._client.request(
            f"/v1/workspaces/{quote(self._workspace, safe='')}/indexes/{quote(index_name, safe='')}"
        )

        raise_for_status(response)

        return Index.model_validate(response.json)

    async def create(self, index_name: str, yaml_config: str, description: str | None = None) -> Index:
        """Create a new index with the given name and configuration.

        :param index_name: Name of the index
        :param yaml_config: YAML configuration for the index
        :param description: Optional description for the index
        :returns: Created index details
        """
        data = {
            "name": index_name,
            "config_yaml": yaml_config,
        }
        if description is not None:
            data["description"] = description

        response = await self._client.request(
            f"v1/workspaces/{quote(self._workspace, safe='')}/indexes", method="POST", data=data
        )

        raise_for_status(response)

        return Index.model_validate(response.json)

    async def update(
        self, index_name: str, updated_index_name: str | None = None, yaml_config: str | None = None
    ) -> Index:
        """Update name and/or configuration of an existing index.

        :param index_name: Name of the index to update
        :param updated_index_name: Optional new name for the index
        :param yaml_config: Optional new YAML configuration
        :returns: Updated index details
        """
        data = {}
        if updated_index_name is not None:
            data["name"] = updated_index_name
        if yaml_config is not None:
            data["config_yaml"] = yaml_config

        if not data:
            raise ValueError("At least one of updated_index_name or yaml_config must be provided")

        response = await self._client.request(
            f"/v1/workspaces/{quote(self._workspace, safe='')}/indexes/{quote(index_name, safe='')}",
            method="PATCH",
            data=data,
        )

        raise_for_status(response)

        return Index.model_validate(response.json)

    async def delete(self, index_name: str) -> None:
        """Delete an index.

        :param index_name: Name of the index to delete.
        """
        response = await self._client.request(
            f"/v1/workspaces/{quote(self._workspace, safe='')}/indexes/{quote(index_name, safe='')}", method="DELETE"
        )

        raise_for_status(response)

    async def deploy(self, index_name: str) -> PipelineValidationResult:
        """Deploy an index.

        :param index_name: Name of the index to deploy.
        :returns: PipelineValidationResult containing deployment status and any errors.
        :raises UnexpectedAPIError: If the API returns an unexpected status code.
        """
        resp = await self._client.request(
            endpoint=f"v1/workspaces/{quote(self._workspace, safe='')}/indexes/{quote(index_name, safe='')}/deploy",
            method="POST",
        )

        # If successful (status 200), the deployment was successful
        if resp.success:
            return PipelineValidationResult(valid=True)

        # Handle validation errors (422)
        if resp.status_code == 422 and resp.json is not None and isinstance(resp.json, dict) and "details" in resp.json:
            errors = [ValidationError(code=error["code"], message=error["message"]) for error in resp.json["details"]]
            return PipelineValidationResult(valid=False, errors=errors)

        # Handle other 4xx errors (400, 404, 424)
        if 400 <= resp.status_code < 500:
            # For non-validation errors, create a generic error
            error_message = resp.text if resp.text else f"HTTP {resp.status_code} error"
            errors = [ValidationError(code="DEPLOYMENT_ERROR", message=error_message)]
            return PipelineValidationResult(valid=False, errors=errors)

        raise UnexpectedAPIError(status_code=resp.status_code, message=resp.text, detail=resp.json)

    async def validate(self, yaml_config: str) -> PipelineValidationResult:
        """Validate an index's YAML configuration against the API.

        :param yaml_config: The YAML configuration string to validate.
        :returns: PipelineValidationResult containing validation status and any errors.
        :raises ValueError: If the YAML is not valid (422 error) or contains syntax errors.
        """
        data = {"indexing_yaml": yaml_config}

        resp = await self._client.request(
            endpoint=f"v1/workspaces/{quote(self._workspace, safe='')}/pipeline_validations",
            method="POST",
            data=data,
        )

        # If successful (status 200), the YAML is valid
        if resp.success:
            return PipelineValidationResult(valid=True)

        if resp.status_code == 400 and resp.json is not None and isinstance(resp.json, dict) and "details" in resp.json:
            errors = [ValidationError(code=error["code"], message=error["message"]) for error in resp.json["details"]]

            return PipelineValidationResult(valid=False, errors=errors)

        if resp.status_code == 422:
            errors = [ValidationError(code="YAML_ERROR", message="Syntax error in YAML")]

            return PipelineValidationResult(valid=False, errors=errors)

        raise UnexpectedAPIError(status_code=resp.status_code, message=resp.text, detail=resp.json)
