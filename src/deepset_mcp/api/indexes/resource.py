# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from deepset_mcp.api.exceptions import UnexpectedAPIError
from deepset_mcp.api.indexes.models import Index, IndexList
from deepset_mcp.api.indexes.protocols import IndexResourceProtocol
from deepset_mcp.api.pipeline.models import PipelineValidationResult, ValidationError
from deepset_mcp.api.protocols import AsyncClientProtocol
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

        response = await self._client.request(f"/v1/workspaces/{self._workspace}/indexes", params=params)

        raise_for_status(response)

        return IndexList.model_validate(response.json)

    async def get(self, index_name: str) -> Index:
        """Get a specific index.

        :param index_name: Name of the index.

        :returns: Index details.
        """
        response = await self._client.request(f"/v1/workspaces/{self._workspace}/indexes/{index_name}")

        raise_for_status(response)

        return Index.model_validate(response.json)

    async def create(self, name: str, yaml_config: str, description: str | None = None) -> Index:
        """Create a new index with the given name and configuration.

        :param name: Name of the index
        :param yaml_config: YAML configuration for the index
        :param description: Optional description for the index
        :returns: Created index details
        """
        data = {
            "name": name,
            "config_yaml": yaml_config,
        }
        if description is not None:
            data["description"] = description

        response = await self._client.request(f"v1/workspaces/{self._workspace}/indexes", method="POST", data=data)

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
            f"/v1/workspaces/{self._workspace}/indexes/{index_name}", method="PATCH", data=data
        )

        raise_for_status(response)

        return Index.model_validate(response.json)

    async def delete(self, index_name: str) -> None:
        """Delete an index.

        :param index_name: Name of the index to delete.
        """
        response = await self._client.request(f"/v1/workspaces/{self._workspace}/indexes/{index_name}", method="DELETE")

        raise_for_status(response)

    async def deploy(self, index_name: str) -> PipelineValidationResult:
        """Deploy an index.

        :param index_name: Name of the index to deploy.
        :returns: PipelineValidationResult containing deployment status and any errors.
        :raises UnexpectedAPIError: If the API returns an unexpected status code.
        """
        resp = await self._client.request(
            endpoint=f"v1/workspaces/{self._workspace}/indexes/{index_name}/deploy",
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
