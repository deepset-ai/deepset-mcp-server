# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from collections.abc import AsyncIterator
from typing import Any

import pytest

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.pipeline.log_level import LogLevel
from deepset_mcp.api.pipeline.models import (
    DeepsetDocument,
    DeepsetPipeline,
    DeepsetSearchResponse,
    DeepsetStreamEvent,
    PipelineList,
    PipelineLogList,
    PipelineValidationResult,
)
from deepset_mcp.api.pipeline.protocols import PipelineResourceProtocol
from deepset_mcp.api.shared_models import NoContentResponse
from deepset_mcp.tools.doc_search import search_docs
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

    async def list(self, page_number: int = 1, limit: int = 10) -> PipelineList:
        raise NotImplementedError

    async def create(self, name: str, yaml_config: str) -> NoContentResponse:
        raise NotImplementedError

    async def update(
        self,
        pipeline_name: str,
        updated_pipeline_name: str | None = None,
        yaml_config: str | None = None,
    ) -> NoContentResponse:
        raise NotImplementedError

    async def get_logs(
        self,
        pipeline_name: str,
        limit: int = 30,
        level: LogLevel | None = None,
    ) -> PipelineLogList:
        raise NotImplementedError

    async def deploy(self, pipeline_name: str) -> PipelineValidationResult:
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


@pytest.mark.asyncio
async def test_search_docs_success() -> None:
    """Test successful docs search."""
    doc_1 = DeepsetDocument(
        content="The deepset platform provides powerful search capabilities.",
        meta={"original_file_path": "/path/to/file.md", "source_id": "123"},
    )

    doc_1_1 = DeepsetDocument(
        content="It is developed by deepset.",
        meta={"original_file_path": "/path/to/file.md", "source_id": "123"},
    )

    doc_2 = DeepsetDocument(
        content="The deepset platform is great.",
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

    assert "The deepset platform provides powerful search capabilities. It is developed by deepset." in result
    assert "The deepset platform is great." in result
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
