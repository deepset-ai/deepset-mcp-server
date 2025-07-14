# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any

from deepset_mcp.api.exceptions import UnexpectedAPIError
from deepset_mcp.api.pipeline_template.models import PipelineTemplate, PipelineTemplateList
from deepset_mcp.api.pipeline_template.protocols import PipelineTemplateResourceProtocol
from deepset_mcp.api.protocols import AsyncClientProtocol
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

    async def list_templates(
        self, limit: int = 100, field: str = "created_at", order: str = "DESC", filter: str | None = None
    ) -> PipelineTemplateList:
        """List pipeline templates in the configured workspace.

        Parameters
        ----------
        limit : int, optional (default=100)
            Maximum number of templates to return
        field : str, optional (default="created_at")
            Field to sort by
        order : str, optional (default="DESC")
            Sort order (ASC or DESC)
        filter : str | None, optional (default=None)
            OData filter expression for filtering templates

        Returns
        -------
        PipelineTemplateList
            List of pipeline templates with metadata
        """
        params = {"limit": limit, "page_number": 1, "field": field, "order": order}

        if filter is not None:
            params["filter"] = filter

        response = await self._client.request(
            f"/v1/workspaces/{self._workspace}/pipeline_templates",
            method="GET",
            params=params,
        )

        raise_for_status(response)

        if response.json is None:
            raise UnexpectedAPIError(message="Unexpected API response, no templates returned.")

        response_data: dict[str, Any] = response.json

        return PipelineTemplateList(
            data=[PipelineTemplate.model_validate(template) for template in response_data["data"]],
            has_more=response_data.get("has_more", False),
            total=response_data.get("total", len(response_data["data"])),
        )
