from types import TracebackType
from typing import Any, Protocol, Self

import pytest
from httpx import Response

from deepset_mcp.api.protocols import AsyncClientProtocol


class FakeClient(AsyncClientProtocol):
    """Fake client for testing."""

    def __init__(self):
        self.responses: list[Response] = []
        self._pipeline_template_responses = {
            "test_template": {
                "author": "deepset",
                "available_to_all_organization_types": True,
                "best_for": ["qa"],
                "deepset_cloud_version": "v2",
                "description": "Test template",
                "expected_output": ["answers"],
                "pipeline_name": "test_template",
                "pipeline_template_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "pipeline_type": "query",
                "potential_applications": ["qa"],
                "query_yaml": "test: yaml",
                "recommended_dataset": ["test"],
                "tags": [{"name": "test", "tag_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"}]
            },
            "list": {
                "data": [
                    {
                        "author": "deepset",
                        "available_to_all_organization_types": True,
                        "best_for": ["qa"],
                        "deepset_cloud_version": "v2",
                        "description": "Template 1",
                        "expected_output": ["answers"],
                        "pipeline_name": "template_1",
                        "pipeline_template_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "pipeline_type": "query",
                        "potential_applications": ["qa"],
                        "query_yaml": "test: yaml",
                        "recommended_dataset": ["test"],
                        "tags": [{"name": "test", "tag_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"}]
                    },
                    {
                        "author": "deepset",
                        "available_to_all_organization_types": True,
                        "best_for": ["qa"],
                        "deepset_cloud_version": "v2",
                        "description": "Template 2",
                        "expected_output": ["answers"],
                        "pipeline_name": "template_2",
                        "pipeline_template_id": "3fa85f64-5717-4562-b3fc-2c963f66afa7",
                        "pipeline_type": "query",
                        "potential_applications": ["qa"],
                        "query_yaml": "test: yaml",
                        "recommended_dataset": ["test"],
                        "tags": [{"name": "test", "tag_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"}]
                    }
                ],
                "has_more": False,
                "total": 2
            }
        }

    async def request(
        self,
        endpoint: str,
        method: str = "GET",
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        """Fake a request by returning a predefined response."""
        if "pipeline_templates" in endpoint:
            if endpoint.endswith("test_template"):
                return Response(200, json=self._pipeline_template_responses["test_template"])
            return Response(200, json=self._pipeline_template_responses["list"])
        return self.responses.pop(0)

    async def close(self) -> None:
        """Clean up resources."""
        pass

    async def __aenter__(self) -> Self:
        """Enter the async context."""
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> bool:
        """Exit the async context."""
        await self.close()
        return False

    def pipelines(self, workspace: str) -> Protocol:
        """Mock pipeline resource."""
        return Protocol()

    def haystack_service(self) -> Protocol:
        """Mock haystack service."""
        return Protocol()

    def pipeline_templates(self, workspace: str) -> Protocol:
        """Mock pipeline template resource."""
        return Protocol()


@pytest.fixture
def fake_client() -> FakeClient:
    """Create a fake client for testing."""
    return FakeClient()
