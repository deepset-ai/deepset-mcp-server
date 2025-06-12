#!/usr/bin/env python3
"""Quick test to validate search functionality."""

import asyncio
from typing import Any

from deepset_mcp.api.pipeline.models import SearchResponse, FilterCondition, SearchFilters
from deepset_mcp.api.pipeline.resource import PipelineResource
from deepset_mcp.api.transport import TransportResponse
from test.unit.conftest import BaseFakeClient


class TestClient(BaseFakeClient):
    def pipelines(self, workspace: str):
        return PipelineResource(client=self, workspace=workspace)


async def test_basic_search():
    """Test basic search functionality."""
    # Create sample search response
    search_response = {
        "query_id": "123e4567-e89b-12d3-a456-426614174000",
        "results": [
            {
                "query": "test query",
                "query_id": "123e4567-e89b-12d3-a456-426614174000",
                "answers": [
                    {
                        "answer": "This is a test answer",
                        "score": 0.95,
                    }
                ],
                "documents": [
                    {
                        "content": "This is test content",
                        "meta": {"source": "test.txt"},
                        "score": 0.9,
                    }
                ],
            }
        ],
    }

    # Create client with predefined response
    client = TestClient(responses={"test-workspace/pipelines/test-pipeline/search": search_response})

    # Create resource and call search method
    resource = client.pipelines("test-workspace")
    result = await resource.search(pipeline_name="test-pipeline", query="test query")

    # Verify results
    assert isinstance(result, SearchResponse)
    assert len(result.results) == 1
    assert len(result.results[0].answers) == 1
    assert result.results[0].answers[0].answer == "This is a test answer"
    assert len(result.results[0].documents) == 1
    assert result.results[0].documents[0].content == "This is test content"
    assert result.results[0].documents[0].meta == {"source": "test.txt"}

    print("✅ Basic search test passed!")


async def test_search_with_filters():
    """Test search with filters."""
    # Create sample search response
    search_response = {
        "query_id": "123e4567-e89b-12d3-a456-426614174000",
        "results": [{"query": "filtered query", "answers": [], "documents": []}],
    }

    # Create client with predefined response
    client = TestClient(responses={"test-workspace/pipelines/test-pipeline/search": search_response})

    # Create resource and call search method with filters
    resource = client.pipelines("test-workspace")
    filters = SearchFilters(
        conditions=[
            FilterCondition(field="filename", value="test.txt"),
            FilterCondition(field="date_created", operator="<=", value="22.12.2023"),
        ]
    )
    result = await resource.search(pipeline_name="test-pipeline", query="filtered query", filters=filters)

    # Verify results
    assert isinstance(result, SearchResponse)

    # Verify request includes filters
    expected_filters = {
        "conditions": [
            {"field": "filename", "value": "test.txt", "operator": None},
            {"field": "date_created", "operator": "<=", "value": "22.12.2023"},
        ]
    }
    assert client.requests[0]["data"] == {
        "queries": ["filtered query"],
        "debug": False,
        "view_prompts": False,
        "filters": expected_filters,
    }

    print("✅ Search with filters test passed!")


if __name__ == "__main__":
    asyncio.run(test_basic_search())
    asyncio.run(test_search_with_filters())
    print("🎉 All tests passed!")