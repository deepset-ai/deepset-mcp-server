from typing import TYPE_CHECKING, Any

from deepset_mcp.api.exceptions import UnexpectedAPIError
from deepset_mcp.api.pipeline.models import (
    DeepsetPipeline,
    NoContentResponse,
    PipelineValidationResult,
    ValidationError,
)
from deepset_mcp.api.protocols import AsyncClientProtocol, PipelineResourceProtocol
from deepset_mcp.api.transport import raise_for_status

if TYPE_CHECKING:
    from deepset_mcp.api.pipeline.handle import PipelineHandle


class PipelineResource(PipelineResourceProtocol):
    """Manages interactions with the deepset pipeline API."""

    def __init__(
        self,
        client: AsyncClientProtocol,
        workspace: str,
    ) -> None:
        """Initializes a PipelineResource instance."""
        self._client = client
        self._workspace = workspace

    async def validate(self, yaml_config: str) -> PipelineValidationResult:
        """
        Validate a pipeline's YAML configuration against the API.

        Args:
            yaml_config: The YAML configuration string to validate

        Returns:
            PipelineValidationResult containing validation status and any errors

        Raises:
            ValueError: If the YAML is not valid (422 error) or contains syntax errors
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
    ) -> list["PipelineHandle"]:
        """
        Retrieve pipeline in the configured workspace with optional pagination.

        :param page_number: Page number for paging.
        :param limit: Max number of items to return.
        :return: List of PipelineHandle instances.
        """
        from deepset_mcp.api.pipeline.handle import PipelineHandle
        
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
        else:
            pipelines = []

        return [PipelineHandle(pipeline=pipeline, resource=self) for pipeline in pipelines]

    async def get(self, pipeline_name: str, include_yaml: bool = True) -> PipelineHandle:
        """Fetch a single pipeline by its name."""
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

        return PipelineHandle(pipeline=pipeline, resource=self)

    async def create(self, name: str, yaml_config: str) -> NoContentResponse:
        """Create a new pipeline with a name and YAML config."""
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
        """Update name and/or YAML config of an existing pipeline."""
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
