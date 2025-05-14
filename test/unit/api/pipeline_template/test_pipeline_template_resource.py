from uuid import UUID

import pytest

from deepset_mcp.api.pipeline_template.models import PipelineTemplate, PipelineTemplateTag
from deepset_mcp.api.pipeline_template.resource import PipelineTemplateResource
from deepset_mcp.api.protocols import PipelineTemplateResourceProtocol
from test.unit.conftest import BaseFakeClient


def create_sample_template(
    name: str = "test-template",
    pipeline_type: str = "query",
    author: str = "deepset-ai",
    description: str = "A test template",
    template_id: str = "3fa85f64-5717-4562-b3fc-2c963f66afa6",
) -> dict:
    """Create a sample pipeline template response dictionary for testing."""
    return {
        "name": name,
        "pipeline_template_id": template_id,
        "pipeline_type": pipeline_type,
        "author": author,
        "description": description,
        "deepset_cloud_version": "v2",
        "pipeline_name": name,
        "query_yaml": "version: '1.0'\ncomponents: []\npipeline:\n  name: test",
        "available_to_all_organization_types": True,
        "best_for": ["quick-start", "testing"],
        "expected_output": ["answers", "documents"],
        "potential_applications": ["testing", "development"],
        "recommended_dataset": ["sample-data"],
        "tags": [
            {
                "name": "test",
                "tag_id": "d4a85f64-5717-4562-b3fc-2c963f66afa6"
            }
        ]
    }


class DummyClient(BaseFakeClient):
    """Dummy client for testing that implements AsyncClientProtocol."""
    def pipeline_templates(self, workspace: str) -> PipelineTemplateResourceProtocol:
        return PipelineTemplateResource(client=self, workspace=workspace)
