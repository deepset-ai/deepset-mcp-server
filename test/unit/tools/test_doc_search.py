# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from collections.abc import AsyncIterator, Sequence
from typing import Any

import pytest

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.pipeline.models import (
    DeepsetDocument,
    DeepsetPipeline,
    DeepsetSearchResponse,
    DeepsetStreamEvent,
    LogLevel,
    PipelineDebugBreakpoint,
    PipelineDebugResult,
    PipelineLog,
    PipelineValidationResult,
    PipelineVersion,
)
from deepset_mcp.api.pipeline.protocols import PipelineResourceProtocol
from deepset_mcp.api.shared_models import NoContentResponse, PaginatedResponse
from deepset_mcp.tools.doc_search import (
    format_docs_search_response,
    list_doc_sections,
    search_docs,
    search_docs_via_docs_api,
)
from test.unit.conftest import BaseFakeClient


class FakeDocsClient(BaseFakeClient):
    def __init__(
        self,
        search_response: DeepsetSearchResponse | None = None,
        search_exception: Exception | None = None,
    ) -> None:
        self._search_response = search_response
        self._search_exception = search_exception
        super().__init__()

    def pipelines(self, workspace: str) -> "FakeDocsPipelineResource":
        return FakeDocsPipelineResource(
            search_response=self._search_response,
            search_exception=self._search_exception,
        )


class FakeDocsPipelineResource(PipelineResourceProtocol):
    def __init__(
        self,
        search_response: DeepsetSearchResponse | None = None,
        search_exception: Exception | None = None,
    ) -> None:
        self._search_response = search_response
        self._search_exception = search_exception

    async def get(self, pipeline_name: str, include_yaml: bool = True) -> DeepsetPipeline:
        raise NotImplementedError

    async def search(
        self,
        pipeline_name: str,
        query: str,
        debug: bool = False,
        view_prompts: bool = False,
        params: dict[str, Any] | None = None,
        filters: dict[str, Any] | None = None,
    ) -> DeepsetSearchResponse:
        if self._search_exception:
            raise self._search_exception
        if self._search_response:
            return self._search_response
        raise NotImplementedError

    # Required by protocol but not used in our tests - providing minimal implementations
    async def validate(self, yaml_config: str) -> PipelineValidationResult:
        raise NotImplementedError

    async def list(
        self, limit: int = 10, after: str | None = None, before: str | None = None
    ) -> PaginatedResponse[DeepsetPipeline]:
        raise NotImplementedError

    async def create(self, pipeline_name: str, yaml_config: str) -> NoContentResponse:
        raise NotImplementedError

    async def list_versions(
        self, pipeline_name: str, limit: int = 10, after: str | None = None
    ) -> PaginatedResponse[PipelineVersion]:
        raise NotImplementedError

    async def create_version(
        self,
        pipeline_name: str,
        config_yaml: str,
        description: str | None = None,
        is_draft: bool = False,
    ) -> PipelineVersion:
        raise NotImplementedError

    async def get_version(self, pipeline_name: str, version_id: str, include_yaml: bool = True) -> PipelineVersion:
        raise NotImplementedError

    async def patch_version(
        self,
        pipeline_name: str,
        version_id: str,
        config_yaml: str | None = None,
        description: str | None = None,
        is_draft: bool | None = None,
    ) -> PipelineVersion:
        raise NotImplementedError

    async def restore_version(self, pipeline_name: str, version_id: str) -> PipelineVersion:
        raise NotImplementedError

    async def get_logs(
        self,
        pipeline_name: str,
        limit: int = 30,
        level: LogLevel | None = None,
        after: str | None = None,
    ) -> PaginatedResponse[PipelineLog]:
        raise NotImplementedError

    async def deploy(self, pipeline_name: str, version_id: str | None = None) -> PipelineValidationResult:
        raise NotImplementedError

    def search_stream(
        self,
        pipeline_name: str,
        query: str,
        debug: bool = False,
        view_prompts: bool = False,
        params: dict[str, Any] | None = None,
        filters: dict[str, Any] | None = None,
    ) -> AsyncIterator[DeepsetStreamEvent]:
        raise NotImplementedError

    async def delete(self, pipeline_name: str) -> NoContentResponse:
        raise NotImplementedError

    async def debug(
        self,
        *,
        pipeline_config: dict[str, Any],
        inputs: dict[str, Any] | None = None,
        break_at: PipelineDebugBreakpoint | None = None,
        resume_from: dict[str, Any] | None = None,
        files: Sequence[str] | None = None,
        pipeline_id: str | None = None,
        pipeline_version_id: str | None = None,
        dry_run: bool = False,
    ) -> PipelineDebugResult:
        raise NotImplementedError


@pytest.mark.asyncio
async def test_search_docs_success() -> None:
    """Test successful docs search."""
    doc_1 = DeepsetDocument(
        content="The Haystack Enterprise Platform provides powerful search capabilities.",
        meta={"original_file_path": "/path/to/file.md", "source_id": "123"},
    )

    doc_1_1 = DeepsetDocument(
        content="It is developed by deepset.",
        meta={"original_file_path": "/path/to/file.md", "source_id": "123"},
    )

    doc_2 = DeepsetDocument(
        content="The Haystack Enterprise Platform is great.",
        meta={"original_file_path": "/path/to/file_2.md", "source_id": "456"},
    )

    search_response = DeepsetSearchResponse(
        query="How to use deepset search?",
        documents=[doc_1, doc_1_1, doc_2],
    )

    client = FakeDocsClient(search_response=search_response)

    result = await search_docs(
        client=client,
        workspace="docs-workspace",
        pipeline_name="docs-search-pipeline",
        query="How to use deepset search?",
    )

    assert (
        "The Haystack Enterprise Platform provides powerful search capabilities. It is developed by deepset." in result
    )
    assert "The Haystack Enterprise Platform is great." in result
    assert "path/to/file_2.md" in result
    assert "path/to/file.md" in result


@pytest.mark.asyncio
async def test_search_docs_pipeline_not_found() -> None:
    """Test docs search with non-existent pipeline."""
    client = FakeDocsClient(search_exception=ResourceNotFoundError())

    result = await search_docs(
        client=client,
        workspace="docs-workspace",
        pipeline_name="missing-pipeline",
        query="test query",
    )

    assert "There is no documentation pipeline named 'missing-pipeline' in workspace 'docs-workspace'" in result


@pytest.mark.asyncio
async def test_search_docs_search_error() -> None:
    """Test docs search with API error during search."""
    client = FakeDocsClient(search_exception=BadRequestError("Search failed"))

    result = await search_docs(
        client=client,
        workspace="docs-workspace",
        pipeline_name="docs-search-pipeline",
        query="test query",
    )

    assert "Failed to search documentation using pipeline 'docs-search-pipeline': Search failed" in result


@pytest.mark.asyncio
async def test_search_docs_unexpected_error() -> None:
    """Test docs search with unexpected API error."""
    client = FakeDocsClient(
        search_exception=UnexpectedAPIError(status_code=500, message="Internal server error"),
    )

    result = await search_docs(
        client=client,
        workspace="docs-workspace",
        pipeline_name="docs-search-pipeline",
        query="test query",
    )

    assert "Failed to search documentation using pipeline 'docs-search-pipeline': Internal server error" in result


def test_format_docs_search_response_includes_titles_and_urls() -> None:
    """The public docs-search formatter should surface titles and URLs like the docs MCP."""
    formatted = format_docs_search_response(
        {
            "results": [
                {
                    "query": "deploy a pipeline",
                    "answers": [
                        {
                            "answer": "Deploy the latest saved version.",
                            "type": "generative",
                            "score": 0.91,
                            "meta": {
                                "title": "Deploy a Pipeline",
                                "url": "/docs/deploy-a-pipeline",
                            },
                        }
                    ],
                    "documents": [
                        {
                            "content": "After you create and save a pipeline, deploy it.",
                            "score": 0.88,
                            "meta": {
                                "heading": "Deploy a Pipeline",
                                "url": "https://docs.cloud.deepset.ai/docs/deploy-a-pipeline",
                            },
                        }
                    ],
                }
            ]
        }
    )

    assert "# Search Results for: deploy a pipeline" in formatted
    assert "Deploy the latest saved version." in formatted
    assert "**URL:** https://docs.cloud.deepset.ai/docs/deploy-a-pipeline" in formatted
    assert "### 1. Deploy a Pipeline" in formatted


def test_format_docs_search_response_empty() -> None:
    """An empty result list should return a no-results message."""
    assert format_docs_search_response({"results": []}) == "No results found for your query."


@pytest.mark.asyncio
async def test_list_doc_sections() -> None:
    """The section list should include the same navigation groups as the docs MCP."""
    result = await list_doc_sections()

    assert "Base URL: https://docs.cloud.deepset.ai" in result
    assert "## Getting Started" in result
    assert "https://docs.cloud.deepset.ai/docs/how-to-guides" in result
    assert "REST API reference documentation" in result


@pytest.mark.asyncio
async def test_search_docs_via_docs_api_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Public docs search should format the API payload and not require a share token."""

    class FakeResponse:
        status_code = 200

        def json(self) -> dict[str, object]:
            return {
                "results": [
                    {
                        "query": "RAG",
                        "answers": [],
                        "documents": [
                            {
                                "content": "Build a RAG pipeline.",
                                "score": 0.75,
                                "meta": {
                                    "heading": "Create a RAG Pipeline",
                                    "url": "https://docs.cloud.deepset.ai/docs/rag",
                                },
                            }
                        ],
                    }
                ]
            }

    class FakeAsyncClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, url: str, json: dict[str, str]) -> FakeResponse:
            assert url == "https://docs.cloud.deepset.ai/api/search"
            assert json == {"query": "RAG"}
            return FakeResponse()

    monkeypatch.setattr("deepset_mcp.tools.doc_search.httpx.AsyncClient", FakeAsyncClient)

    result = await search_docs_via_docs_api(query="RAG")

    assert "Create a RAG Pipeline" in result
    assert "https://docs.cloud.deepset.ai/docs/rag" in result
    assert "Build a RAG pipeline." in result


@pytest.mark.asyncio
async def test_search_docs_via_docs_api_empty_query() -> None:
    """A missing query should fail fast without calling the search API."""
    result = await search_docs_via_docs_api(query="")
    assert result == "Error: No query provided."
