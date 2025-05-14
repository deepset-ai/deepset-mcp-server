from typing import Any

from deepset_mcp.api.exceptions import UnexpectedAPIError
from deepset_mcp.api.pipeline_template.models import PipelineTemplate
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.api.transport import raise_for_status


class PipelineTemplateResource:
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

    async def list_templates(self, limit: int = 100) -> list[PipelineTemplate]:
        """List pipeline templates in the configured workspace.

        Parameters
        ----------
        limit : int, optional (default=100)
            Maximum number of templates to return

        Returns
        -------
        list[PipelineTemplate]
            List of pipeline templates
        """
        response = await self._client.request(
            f"/v1/workspaces/{self._workspace}/pipeline_templates?limit={limit}&page_number=1&field=created_at&order=DESC",
            method="GET",
        )

        raise_for_status(response)

        if response.json is None:
            raise UnexpectedAPIError(message="Unexpected API response, no templates returned.")

        response_data: dict[str, Any] = response.json

        return [PipelineTemplate.model_validate(template) for template in response_data["data"]]
