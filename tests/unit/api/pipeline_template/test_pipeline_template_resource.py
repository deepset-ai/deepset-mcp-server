from uuid import UUID

import pytest

from deepset_mcp.api.pipeline_template.models import PipelineTemplate, PipelineTemplateTag
from deepset_mcp.api.pipeline_template.resource import PipelineTemplateResource


class TestPipelineTemplateResource:
    @pytest.fixture
    def workspace(self) -> str:
        return "test_workspace"

    @pytest.fixture
    def resource(self, fake_client, workspace) -> PipelineTemplateResource:
        return PipelineTemplateResource(client=fake_client, workspace=workspace)

    async def test_get_template(self, resource):
        template = await resource.get_template("test_template")
        assert isinstance(template, PipelineTemplate)
        assert template.template_name == "test_template"

    async def test_list_templates(self, resource):
        templates = await resource.list_templates(limit=100)
        assert isinstance(templates, list)
        assert len(templates) == 2
        assert all(isinstance(template, PipelineTemplate) for template in templates)
