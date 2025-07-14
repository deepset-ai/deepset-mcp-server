# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import json
import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from deepset_mcp.api.exceptions import UnexpectedAPIError
from deepset_mcp.api.pipeline.log_level import LogLevel
from deepset_mcp.api.pipeline.models import (
    DeepsetPipeline,
    DeepsetSearchResponse,
    DeepsetStreamEvent,
    PipelineList,
    PipelineLogList,
    PipelineValidationResult,
    ValidationError,
)
from deepset_mcp.api.pipeline.protocols import PipelineResourceProtocol
from deepset_mcp.api.shared_models import NoContentResponse
from deepset_mcp.api.transport import raise_for_status

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from deepset_mcp.api.protocols import AsyncClientProtocol


class PipelineResource(PipelineResourceProtocol):
    """Manages interactions with the deepset pipeline API."""

    def __init__(
        self,
        client: "AsyncClientProtocol",
        workspace: str,
    ) -> None:
        """Initializes a PipelineResource instance.

        :param client: The async client protocol instance.
        :param workspace: The workspace identifier.
        """
        self._client = client
        self._workspace = workspace

    async def validate(self, yaml_config: str) -> PipelineValidationResult:
        """Validate a pipeline's YAML configuration against the API.

        :param yaml_config: The YAML configuration string to validate.
        :returns: PipelineValidationResult containing validation status and any errors.
        :raises ValueError: If the YAML is not valid (422 error) or contains syntax errors.
        """
        data = {"query_yaml": yaml_config}

        resp = await self._client.request(
            endpoint=f"v1/workspaces/{self._workspace}/pipeline_validations",
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

    async def list(
        self,
        page_number: int = 1,
        limit: int = 10,
    ) -> PipelineList:
        """Retrieve pipeline in the configured workspace with optional pagination.

        :param page_number: Page number for paging.
        :param limit: Max number of items to return.
        :returns: PipelineList with pipelines and metadata.
        """
        params: dict[str, Any] = {
            "page_number": page_number,
            "limit": limit,
        }

        resp = await self._client.request(
            endpoint=f"v1/workspaces/{self._workspace}/pipelines",
            method="GET",
            params=params,
        )

        raise_for_status(resp)

        response = resp.json

        if response is not None:
            pipelines = [DeepsetPipeline.model_validate(item) for item in response.get("data", [])]
            return PipelineList(
                data=pipelines,
                has_more=response.get("has_more", False),
                total=response.get("total", len(pipelines)),
            )
        else:
            return PipelineList(data=[], has_more=False, total=0)

    async def get(self, pipeline_name: str, include_yaml: bool = True) -> DeepsetPipeline:
        """Fetch a single pipeline by its name.

        :param pipeline_name: Name of the pipeline to fetch.
        :param include_yaml: Whether to include YAML configuration in the response.
        :returns: DeepsetPipeline instance.
        """
        resp = await self._client.request(endpoint=f"v1/workspaces/{self._workspace}/pipelines/{pipeline_name}")
        raise_for_status(resp)

        pipeline = DeepsetPipeline.model_validate(resp.json)

        if include_yaml:
            yaml_response = await self._client.request(
                endpoint=f"v1/workspaces/{self._workspace}/pipelines/{pipeline_name}/yaml"
            )

            raise_for_status(yaml_response)

            if yaml_response.json is not None:
                pipeline.yaml_config = yaml_response.json["query_yaml"]

        return pipeline

    async def create(self, name: str, yaml_config: str) -> NoContentResponse:
        """Create a new pipeline with a name and YAML config.

        :param name: Name of the new pipeline.
        :param yaml_config: YAML configuration for the pipeline.
        :returns: NoContentResponse indicating successful creation.
        """
        data = {"name": name, "query_yaml": yaml_config}
        resp = await self._client.request(
            endpoint=f"v1/workspaces/{self._workspace}/pipelines",
            method="POST",
            data=data,
        )

        raise_for_status(resp)

        return NoContentResponse(message="Pipeline created successfully.")

    async def update(
        self,
        pipeline_name: str,
        updated_pipeline_name: str | None = None,
        yaml_config: str | None = None,
    ) -> NoContentResponse:
        """Update name and/or YAML config of an existing pipeline.

        :param pipeline_name: Current name of the pipeline.
        :param updated_pipeline_name: New name for the pipeline (optional).
        :param yaml_config: New YAML configuration (optional).
        :returns: NoContentResponse indicating successful update.
        :raises ValueError: If neither updated_pipeline_name nor yaml_config is provided.
        """
        # Handle name update first if any
        if updated_pipeline_name is not None:
            name_resp = await self._client.request(
                endpoint=f"v1/workspaces/{self._workspace}/pipelines/{pipeline_name}",
                method="PATCH",
                data={"name": updated_pipeline_name},
            )

            raise_for_status(name_resp)

            pipeline_name = updated_pipeline_name

            if yaml_config is None:
                return NoContentResponse(message="Pipeline name updated successfully.")

        if yaml_config is not None:
            yaml_resp = await self._client.request(
                endpoint=f"v1/workspaces/{self._workspace}/pipelines/{pipeline_name}/yaml",
                method="PUT",
                data={"query_yaml": yaml_config},
            )

            raise_for_status(yaml_resp)

            if updated_pipeline_name is not None:
                response = NoContentResponse(message="Pipeline name and YAML updated successfully.")
            else:
                response = NoContentResponse(message="Pipeline YAML updated successfully.")

            return response

        raise ValueError("Either `updated_pipeline_name` or `yaml_config` must be provided.")

    async def get_logs(
        self,
        pipeline_name: str,
        limit: int = 30,
        level: LogLevel | None = None,
    ) -> PipelineLogList:
        """Fetch logs for a specific pipeline.

        :param pipeline_name: Name of the pipeline to fetch logs for.
        :param limit: Maximum number of log entries to return.
        :param level: Filter logs by level. If None, returns all levels.
        :returns: A PipelineLogList containing the log entries.
        """
        params: dict[str, Any] = {
            "limit": limit,
            "filter": "origin eq 'querypipeline'",
        }

        # Add level filter if specified
        if level is not None:
            params["filter"] = f"level eq '{level}' and origin eq 'querypipeline'"

        resp = await self._client.request(
            endpoint=f"v1/workspaces/{self._workspace}/pipelines/{pipeline_name}/logs",
            method="GET",
            params=params,
        )

        raise_for_status(resp)

        if resp.json is not None:
            return PipelineLogList.model_validate(resp.json)
        else:
            # Return empty log list if no response
            return PipelineLogList(data=[], has_more=False, total=0)

    async def deploy(self, pipeline_name: str) -> PipelineValidationResult:
        """Deploy a pipeline to production.

        :param pipeline_name: Name of the pipeline to deploy.
        :returns: PipelineValidationResult containing deployment status and any errors.
        :raises UnexpectedAPIError: If the API returns an unexpected status code.
        """
        resp = await self._client.request(
            endpoint=f"v1/workspaces/{self._workspace}/pipelines/{pipeline_name}/deploy",
            method="POST",
        )

        # If successful (status 200), the deployment was successful
        if resp.success:
            return PipelineValidationResult(valid=True)

        # Handle validation errors (422)
        if resp.status_code == 422 and resp.json is not None and isinstance(resp.json, dict) and "details" in resp.json:
            errors = [ValidationError(code=error["code"], message=error["message"]) for error in resp.json["details"]]
            return PipelineValidationResult(valid=False, errors=errors)

        # Handle other 4xx errors (400, 404)
        if 400 <= resp.status_code < 500:
            # For non-validation errors, create a generic error
            error_message = resp.text if resp.text else f"HTTP {resp.status_code} error"
            errors = [ValidationError(code="DEPLOYMENT_ERROR", message=error_message)]
            return PipelineValidationResult(valid=False, errors=errors)

        raise UnexpectedAPIError(status_code=resp.status_code, message=resp.text, detail=resp.json)

    async def delete(self, pipeline_name: str) -> NoContentResponse:
        """Delete a pipeline.

        :param pipeline_name: Name of the pipeline to delete.
        :returns: NoContentResponse indicating successful deletion.
        :raises UnexpectedAPIError: If the API returns an unexpected status code.
        """
        resp = await self._client.request(
            endpoint=f"v1/workspaces/{self._workspace}/pipelines/{pipeline_name}",
            method="DELETE",
        )

        raise_for_status(resp)

        return NoContentResponse(message="Pipeline deleted successfully.")

    async def search(
        self,
        pipeline_name: str,
        query: str,
        debug: bool = False,
        view_prompts: bool = False,
        params: dict[str, Any] | None = None,
        filters: dict[str, Any] | None = None,
    ) -> DeepsetSearchResponse:
        """Search using a pipeline.

        :param pipeline_name: Name of the pipeline to use for search.
        :param query: Search query.
        :param debug: Whether to include debug information.
        :param view_prompts: Whether to include prompts in the response.
        :param params: Additional parameters for pipeline components.
        :param filters: Search filters to apply.
        :returns: SearchResponse containing search results.
        """
        # Prepare request data
        data: dict[str, Any] = {
            "queries": [query],  # API expects a list but we only send one query
            "debug": debug,
            "view_prompts": view_prompts,
        }

        if params:
            data["params"] = params

        if filters:
            data["filters"] = filters

        resp = await self._client.request(
            endpoint=f"v1/workspaces/{self._workspace}/pipelines/{pipeline_name}/search",
            method="POST",
            data=data,
            response_type=dict[str, Any],
            timeout=180.0,
        )

        raise_for_status(resp)

        if resp.json is not None:
            return DeepsetSearchResponse.model_validate(resp.json)
        else:
            # Return empty response if no JSON data
            return DeepsetSearchResponse()

    async def search_stream(
        self,
        pipeline_name: str,
        query: str,
        debug: bool = False,
        view_prompts: bool = False,
        params: dict[str, Any] | None = None,
        filters: dict[str, Any] | None = None,
    ) -> AsyncIterator[DeepsetStreamEvent]:
        """Search using a pipeline with response streaming.

        :param pipeline_name: Name of the pipeline to use for search.
        :param query: Search query.
        :param debug: Whether to include debug information.
        :param view_prompts: Whether to include prompts in the response.
        :param params: Additional parameters for pipeline components.
        :param filters: Search filters to apply.
        :returns: AsyncIterator streaming the result.
        """
        # For streaming, we need to add include_result flag
        # Prepare request data
        data: dict[str, Any] = {
            "query": query,
            "debug": debug,
            "view_prompts": view_prompts,
            "include_result": True,
        }

        if params:
            data["params"] = params

        if filters:
            data["filters"] = filters

        async with self._client.stream_request(
            endpoint=f"v1/workspaces/{self._workspace}/pipelines/{pipeline_name}/search-stream",
            method="POST",
            data=data,
        ) as resp:
            async for line in resp.iter_lines():
                try:
                    event_dict = json.loads(line)
                    event = DeepsetStreamEvent.model_validate(event_dict)

                    if event.error is not None:
                        raise UnexpectedAPIError(message=event.error)
                    yield event
                except (json.JSONDecodeError, ValueError):
                    # Skip malformed events
                    continue
