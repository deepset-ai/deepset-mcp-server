from typing import Any

from deepset_mcp.api.client import AsyncClientProtocol
from deepset_mcp.api.pipeline.models import DeepsetPipeline, PipelineValidationResult, ValidationError


class PipelineResource:
    """Manages interactions with the deepset pipeline API."""

    def __init__(
        self,
        client: AsyncClientProtocol,
        workspace: str,
    ) -> None:
        """Initializes a PipelineResource instance."""
        self._client = client
        self._workspace = workspace

    async def list(
        self,
        page_number: int = 1,
        limit: int = 10,
    ) -> list[DeepsetPipeline]:
        """
        Retrieve pipeline in the configured workspace with optional pagination.

        :param page_number: Page number for paging.
        :param limit: Max number of items to return.
        :return: PipelineListResponse containing `data`, `has_more`, and `total`.
        """
        params: dict[str, Any] = {
            "page_number": page_number,
            "limit": limit,
        }

        query = "?" + "&".join(f"{k}={v}" for k, v in params.items()) if params else ""
        resp = await self._client.request(
            endpoint=f"v1/workspaces/{self._workspace}/pipelines{query}",
            method="GET",
        )

        response = resp.json

        if response is not None:
            pipelines = [DeepsetPipeline.model_validate(item) for item in response.get("data", [])]
        else:
            pipelines = []

        return pipelines

    async def get(self, pipeline_name: str, include_yaml: bool = True) -> DeepsetPipeline:
        """Fetch a single pipeline by its name."""
        resp = await self._client.request(endpoint=f"v1/workspaces/{self._workspace}/pipelines/{pipeline_name}")
        pipeline = DeepsetPipeline.model_validate(resp.json)

        if include_yaml:
            yaml_response = await self._client.request(
                endpoint=f"v1/workspaces/{self._workspace}/pipelines/{pipeline_name}/yaml"
            )

            if yaml_response.json is not None:
                pipeline.yaml_config = yaml_response.json["query_yaml"]

        return pipeline

    async def create(self, name: str, yaml_config: str) -> None:
        """Create a new pipeline with a name and YAML config."""
        data = {"name": name, "query_yaml": yaml_config}
        await self._client.request(
            endpoint=f"v1/workspaces/{self._workspace}/pipelines",
            method="POST",
            data=data,
        )

    async def update(
        self,
        pipeline_name: str,
        updated_pipeline_name: str | None = None,
        yaml_config: str | None = None,
    ) -> None:
        """Update name and/or YAML config of an existing pipeline."""
        # Handle name update first if any
        if updated_pipeline_name is not None:
            await self._client.request(
                endpoint=f"v1/workspaces/{self._workspace}/pipelines/{pipeline_name}",
                method="PATCH",
                data={"name": updated_pipeline_name},
            )

            pipeline_name = updated_pipeline_name

        if yaml_config is not None:
            await self._client.request(
                endpoint=f"v1/workspaces/{self._workspace}/pipelines/{pipeline_name}/yaml",
                method="PUT",
                data={"query_yaml": yaml_config},
            )


# async with AsyncDeepsetClient() as client:
#    await client.pipelines("default").list()
#    await client.pipelines("default").get("hello")
#    await client.pipelines("default").update(yaml_config="blabla")
