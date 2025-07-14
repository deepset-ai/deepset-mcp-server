# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import pytest

from deepset_mcp.api.exceptions import UnexpectedAPIError
from deepset_mcp.api.pipeline.models import (
    DeepsetSearchResponse,
    DeepsetStreamEvent,
)
from deepset_mcp.api.pipeline.protocols import PipelineResourceProtocol
from deepset_mcp.api.pipeline.resource import PipelineResource
from deepset_mcp.api.transport import TransportResponse
from test.unit.conftest import BaseFakeClient


class DummyClient(BaseFakeClient):
    """Dummy client for testing that implements AsyncClientProtocol."""

    def pipelines(self, workspace: str) -> PipelineResourceProtocol:
        return PipelineResource(client=self, workspace=workspace)


class TestPipelineSearchResource:
    """Tests for the search functionality of the PipelineResource class."""

    @pytest.mark.asyncio
    async def test_search_basic_query(self) -> None:
        """Test basic search with a simple query."""
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
        client = DummyClient(responses={"test-workspace/pipelines/test-pipeline/search": search_response})

        # Create resource and call search method
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.search(pipeline_name="test-pipeline", query="test query")

        # Verify results
        assert isinstance(result, DeepsetSearchResponse)
        assert len(result.answers) == 1
        assert result.answers[0].answer == "This is a test answer"
        assert len(result.documents) == 1
        assert result.documents[0].content == "This is test content"
        assert result.documents[0].meta == {"source": "test.txt"}

        # Verify request
        assert len(client.requests) == 1
        assert client.requests[0]["endpoint"] == "v1/workspaces/test-workspace/pipelines/test-pipeline/search"
        assert client.requests[0]["method"] == "POST"
        assert client.requests[0]["data"] == {
            "queries": ["test query"],
            "debug": False,
            "view_prompts": False,
        }

    @pytest.mark.asyncio
    async def test_search_with_debug_and_prompts(self) -> None:
        """Test search with debug and view_prompts enabled."""
        # Create sample search response with debug and prompts
        search_response = {
            "query_id": "123e4567-e89b-12d3-a456-426614174000",
            "results": [
                {
                    "query": "debug query",
                    "query_id": "123e4567-e89b-12d3-a456-426614174000",
                    "answers": [],
                    "documents": [],
                    "prompts": {"llm": "Answer the question: {query}"},
                    "_debug": {"llm": {"input": "debug info"}},
                }
            ],
        }

        # Create client with predefined response
        client = DummyClient(responses={"test-workspace/pipelines/test-pipeline/search": search_response})

        # Create resource and call search method with debug and prompts
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.search(
            pipeline_name="test-pipeline", query="debug query", debug=True, view_prompts=True
        )

        # Verify results
        assert isinstance(result, DeepsetSearchResponse)
        assert result.prompts == {"llm": "Answer the question: {query}"}
        assert result.debug == {"llm": {"input": "debug info"}}

        # Verify request
        assert client.requests[0]["data"] == {
            "queries": ["debug query"],
            "debug": True,
            "view_prompts": True,
        }

    @pytest.mark.asyncio
    async def test_search_with_params(self) -> None:
        """Test search with additional parameters."""
        # Create sample search response
        search_response = {
            "query_id": "123e4567-e89b-12d3-a456-426614174000",
            "results": [{"query": "param query", "answers": [], "documents": []}],
        }

        # Create client with predefined response
        client = DummyClient(responses={"test-workspace/pipelines/test-pipeline/search": search_response})

        # Create resource and call search method with params
        resource = PipelineResource(client=client, workspace="test-workspace")
        params = {"retriever": '{"top_k": 5}', "llm": '{"temperature": 0.1}'}
        result = await resource.search(pipeline_name="test-pipeline", query="param query", params=params)

        # Verify results
        assert isinstance(result, DeepsetSearchResponse)

        # Verify request includes params
        assert client.requests[0]["data"] == {
            "queries": ["param query"],
            "debug": False,
            "view_prompts": False,
            "params": params,
        }

    @pytest.mark.asyncio
    async def test_search_with_filters(self) -> None:
        """Test search with filters."""
        # Create sample search response
        search_response = {
            "query_id": "123e4567-e89b-12d3-a456-426614174000",
            "results": [{"query": "filtered query", "answers": [], "documents": []}],
        }

        # Create client with predefined response
        client = DummyClient(responses={"test-workspace/pipelines/test-pipeline/search": search_response})

        # Create resource and call search method with filters
        resource = PipelineResource(client=client, workspace="test-workspace")
        filters = {
            "conditions": [
                {"field": "filename", "value": "test.txt", "operator": "=="},
                {"field": "date_created", "operator": "<=", "value": "2020-07-30"},
            ]
        }

        result = await resource.search(pipeline_name="test-pipeline", query="filtered query", filters=filters)

        # Verify results
        assert isinstance(result, DeepsetSearchResponse)

        # Verify request includes filters
        expected_filters = {
            "conditions": [
                {"field": "filename", "value": "test.txt", "operator": "=="},
                {"field": "date_created", "operator": "<=", "value": "2020-07-30"},
            ]
        }
        assert client.requests[0]["data"] == {
            "queries": ["filtered query"],
            "debug": False,
            "view_prompts": False,
            "filters": expected_filters,
        }

    @pytest.mark.asyncio
    async def test_search_empty_response(self) -> None:
        """Test search with empty response."""
        # Create empty search response
        search_response = {"query_id": "123e4567-e89b-12d3-a456-426614174000", "results": []}

        # Create client with predefined response
        client = DummyClient(responses={"test-workspace/pipelines/test-pipeline/search": search_response})

        # Create resource and call search method
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.search(pipeline_name="test-pipeline", query="empty query")

        # Verify results
        assert isinstance(result, DeepsetSearchResponse)
        assert len(result.answers) == 0
        assert len(result.documents) == 0

    @pytest.mark.asyncio
    async def test_search_null_response(self) -> None:
        """Test search with null response."""
        # Create client with null response
        client = DummyClient()
        client.responses = {
            "test-workspace/pipelines/test-pipeline/search": TransportResponse(text="", status_code=200, json=None)
        }

        # Create resource and call search method
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.search(pipeline_name="test-pipeline", query="null query")

        # Verify empty response
        assert isinstance(result, DeepsetSearchResponse)
        assert result.query_id is None

    @pytest.mark.asyncio
    async def test_search_error(self) -> None:
        """Test handling of errors during search."""
        # Create client that raises an exception
        client = DummyClient(responses={"test-workspace/pipelines/test-pipeline/search": ValueError("Search error")})

        # Create resource
        resource = PipelineResource(client=client, workspace="test-workspace")

        # Verify exception is raised
        with pytest.raises(ValueError, match="Search error"):
            await resource.search(pipeline_name="test-pipeline", query="error query")

    @pytest.mark.asyncio
    async def test_search_with_all_parameters(self) -> None:
        """Test search with all parameters combined."""
        # Create comprehensive search response
        search_response = {
            "query_id": "123e4567-e89b-12d3-a456-426614174000",
            "results": [
                {
                    "query": "comprehensive query",
                    "query_id": "123e4567-e89b-12d3-a456-426614174000",
                    "answers": [
                        {
                            "answer": "Comprehensive answer",
                            "context": "Some context",
                            "score": 0.98,
                            "meta": {"confidence": "high"},
                        }
                    ],
                    "documents": [
                        {
                            "content": "Comprehensive content",
                            "meta": {"source": "comprehensive.txt", "author": "test"},
                            "score": 0.95,
                        }
                    ],
                    "prompts": {"llm": "Comprehensive prompt: {query}"},
                    "_debug": {"retriever": {"retrieved_docs": 10}},
                }
            ],
        }

        # Create client with predefined response
        client = DummyClient(responses={"test-workspace/pipelines/test-pipeline/search": search_response})

        # Create resource and call search method with all parameters
        resource = PipelineResource(client=client, workspace="test-workspace")
        params = {"retriever": '{"top_k": 10}'}
        filters = {"field": "author", "operator": "==", "value": "test"}
        result = await resource.search(
            pipeline_name="test-pipeline",
            query="comprehensive query",
            debug=True,
            view_prompts=True,
            params=params,
            filters=filters,
        )

        # Verify results
        assert isinstance(result, DeepsetSearchResponse)
        assert len(result.answers) == 1
        assert result.answers[0].answer == "Comprehensive answer"
        assert result.answers[0].context == "Some context"
        assert len(result.documents) == 1
        assert result.documents[0].content == "Comprehensive content"
        assert result.documents[0].meta == {"source": "comprehensive.txt", "author": "test"}
        assert result.prompts == {"llm": "Comprehensive prompt: {query}"}
        assert result.debug == {"retriever": {"retrieved_docs": 10}}

        # Verify request includes all parameters
        expected_data = {
            "queries": ["comprehensive query"],
            "debug": True,
            "view_prompts": True,
            "params": params,
            "filters": {"field": "author", "value": "test", "operator": "=="},
        }
        assert client.requests[0]["data"] == expected_data

    @pytest.mark.asyncio
    async def test_search_streaming_basic(self) -> None:
        """Test basic streaming search."""
        # Create client with streaming response
        client = BaseFakeClient()
        client.responses = {
            "v1/workspaces/test-workspace/pipelines/test-pipeline/search-stream": {
                "status_code": 200,
                "lines": [
                    '{"query_id": "123e4567-e89b-12d3-a456-426614174000", "type": "delta", "delta": {"text": "Hello"}}',
                    (
                        '{"query_id": "123e4567-e89b-12d3-a456-426614174000", "type": "delta", "delta": '
                        '{"text": " world"}}'
                    ),
                    (
                        '{"query_id": "123e4567-e89b-12d3-a456-426614174000", "type": "result", '
                        '"result": {"query": "streaming_query", "query_id": "123e4567-e89b-12d3-a456-426614174000"}}'
                    ),
                ],
            }
        }

        # Create resource and call search_stream
        resource = PipelineResource(client=client, workspace="test-workspace")

        # Collect stream events
        events = []
        async for event in resource.search_stream(pipeline_name="test-pipeline", query="streaming query"):
            events.append(event)

        # Verify events
        assert len(events) == 3
        assert all(isinstance(event, DeepsetStreamEvent) for event in events)
        assert events[0].type == "delta"
        assert events[0].delta is not None
        assert events[0].delta.text == "Hello"
        assert events[1].type == "delta"
        assert events[1].delta is not None
        assert events[1].delta.text == " world"
        assert events[2].type == "result"
        assert events[2].result is not None
        assert isinstance(events[2].result, DeepsetSearchResponse)

        # Verify request
        assert len(client.requests) == 1
        assert client.requests[0]["endpoint"] == "v1/workspaces/test-workspace/pipelines/test-pipeline/search-stream"
        assert client.requests[0]["method"] == "POST"
        assert client.requests[0].get("streaming") is True  # Flag added by BaseFakeClient
        assert client.requests[0]["data"] == {
            "query": "streaming query",
            "debug": False,
            "view_prompts": False,
            "include_result": True,
        }

    @pytest.mark.asyncio
    async def test_search_streaming_with_params(self) -> None:
        """Test streaming search with additional parameters."""
        # Create client with streaming response
        client = BaseFakeClient()
        client.responses = {
            "v1/workspaces/test-workspace/pipelines/test-pipeline/search-stream": {
                "status_code": 200,
                "lines": [
                    '{"query_id": "123e4567-e89b-12d3-a456-426614174000", "type": "delta", "delta": {"text": "Test"}}'
                ],
            }
        }

        # Create resource and call search_stream with parameters
        resource = PipelineResource(client=client, workspace="test-workspace")
        params = {"retriever": '{"top_k": 5}'}
        filters = {"field": "author", "value": "test", "operator": "=="}

        # Consume the stream
        events = []
        async for event in resource.search_stream(
            pipeline_name="test-pipeline",
            query="param stream query",
            debug=True,
            view_prompts=True,
            params=params,
            filters=filters,
        ):
            events.append(event)

        # Verify request includes all parameters
        expected_data = {
            "query": "param stream query",
            "debug": True,
            "view_prompts": True,
            "params": params,
            "filters": {"field": "author", "value": "test", "operator": "=="},
            "include_result": True,
        }
        assert client.requests[0]["data"] == expected_data

    @pytest.mark.asyncio
    async def test_search_streaming_malformed_events(self) -> None:
        """Test streaming search with malformed events (should be skipped)."""
        # Create client with streaming response including malformed JSON
        client = BaseFakeClient()
        client.responses = {
            "v1/workspaces/test-workspace/pipelines/test-pipeline/search-stream": {
                "status_code": 200,
                "lines": [
                    (
                        '{"query_id": "123e4567-e89b-12d3-a456-426614174000", "type": "delta", '
                        '"delta": {"text": "Good"}}'
                    ),
                    "{malformed json",
                    (
                        '{"query_id": "123e4567-e89b-12d3-a456-426614174000", "type": "delta", '
                        '"delta": {"text": "Also good"}}'
                    ),
                ],
            }
        }

        # Create resource and call search_stream
        resource = PipelineResource(client=client, workspace="test-workspace")

        # Collect stream events (malformed should be skipped)
        events = []
        async for event in resource.search_stream(pipeline_name="test-pipeline", query="malformed test"):
            events.append(event)

        # Verify only good events were processed
        assert len(events) == 2
        assert events[0].delta is not None
        assert events[0].delta.text == "Good"
        assert events[1].delta is not None
        assert events[1].delta.text == "Also good"

    @pytest.mark.asyncio
    async def test_search_streaming_error_handling(self) -> None:
        """Test streaming search error handling."""
        # Create client with error response
        client = BaseFakeClient()
        client.responses = {
            "v1/workspaces/test-workspace/pipelines/test-pipeline/search-stream": {
                "status_code": 404,
                "lines": ['{"type": "error", "error": "Pipeline not found."}'],
            }
        }

        resource = PipelineResource(client=client, workspace="test-workspace")

        with pytest.raises(UnexpectedAPIError):
            async for _ in resource.search_stream(pipeline_name="test-pipeline", query="error test"):
                continue

    @pytest.mark.asyncio
    async def test_search_streaming_with_error_event(self) -> None:
        """Test streaming search with error event in stream."""
        # Create client with streaming response that includes an error event
        client = BaseFakeClient()
        client.responses = {
            "v1/workspaces/test-workspace/pipelines/test-pipeline/search-stream": {
                "status_code": 200,
                "lines": [
                    '{"query_id": "123", "type": "delta", "delta": {"text": "Start"}}',
                    '{"query_id": "123", "type": "error", "error": "Something went wrong"}',
                ],
            }
        }

        # Create resource
        resource = PipelineResource(client=client, workspace="test-workspace")

        # Collect events until error
        events = []
        with pytest.raises(UnexpectedAPIError, match="Something went wrong"):
            async for event in resource.search_stream(pipeline_name="test-pipeline", query="error event test"):
                events.append(event)

        # Should have processed the first event before hitting the error
        assert len(events) == 1
        assert events[0].delta is not None
        assert events[0].delta.text == "Start"
