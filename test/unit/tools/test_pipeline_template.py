from typing import Any
from uuid import UUID, uuid4

import numpy as np
import pytest

from deepset_mcp.api.exceptions import ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.pipeline_template.models import (
    PipelineTemplate,
    PipelineTemplateList,
    PipelineTemplateSearchResults,
    PipelineTemplateTag,
    PipelineType,
)
from deepset_mcp.tools.model_protocol import ModelProtocol
from deepset_mcp.tools.pipeline_template import (
    get_pipeline_template,
    list_pipeline_templates,
    search_pipeline_templates,
)
from test.unit.conftest import BaseFakeClient


class FakeModel(ModelProtocol):
    def encode(self, sentences: list[str] | str) -> np.ndarray[Any, Any]:
        # Convert input to list if it's a single string
        if isinstance(sentences, str):
            sentences = [sentences]

        # Create fake embeddings with consistent similarities
        embeddings = np.zeros((len(sentences), 3))
        for i, sentence in enumerate(sentences):
            if "rag" in sentence.lower() or "retrieval" in sentence.lower():
                embeddings[i] = [1, 0, 0]
            elif "chat" in sentence.lower() or "conversation" in sentence.lower():
                embeddings[i] = [0, 1, 0]
            else:
                embeddings[i] = [0, 0, 1]
        return embeddings


class FakePipelineTemplateResource:
    def __init__(
        self,
        list_response: list[PipelineTemplate] | None = None,
        get_response: PipelineTemplate | None = None,
        list_exception: Exception | None = None,
        get_exception: Exception | None = None,
    ) -> None:
        self._list_response = list_response
        self._get_response = get_response
        self._list_exception = list_exception
        self._get_exception = get_exception
        self.last_list_call_params: dict[str, Any] = {}

    async def list_templates(
        self, limit: int = 100, field: str = "created_at", order: str = "DESC", filter: str | None = None
    ) -> PipelineTemplateList:
        # Store the parameters for verification
        self.last_list_call_params = {"limit": limit, "field": field, "order": order, "filter": filter}

        if self._list_exception:
            raise self._list_exception
        if self._list_response is not None:
            return PipelineTemplateList(
                data=self._list_response, has_more=len(self._list_response) == limit, total=len(self._list_response)
            )
        raise NotImplementedError

    async def get_template(self, template_name: str) -> PipelineTemplate:
        if self._get_exception:
            raise self._get_exception
        if self._get_response is not None:
            return self._get_response
        raise NotImplementedError


class FakeClient(BaseFakeClient):
    def __init__(self, resource: FakePipelineTemplateResource) -> None:
        self._resource = resource
        super().__init__()

    def pipeline_templates(self, workspace: str) -> FakePipelineTemplateResource:
        return self._resource


@pytest.mark.asyncio
async def test_list_pipeline_templates_returns_template_list() -> None:
    template1 = PipelineTemplate(
        pipeline_name="template1",
        name="template1",
        pipeline_template_id=UUID("00000000-0000-0000-0000-000000000001"),
        author="Alice Smith",
        description="First template",
        best_for=["use case 1", "use case 2"],
        potential_applications=["app 1", "app 2"],
        query_yaml="config1: value1",
        tags=[PipelineTemplateTag(name="tag1", tag_id=UUID("10000000-0000-0000-0000-000000000001"))],
        pipeline_type=PipelineType.QUERY,
    )
    template2 = PipelineTemplate(
        pipeline_name="template2",
        name="template2",
        pipeline_template_id=UUID("00000000-0000-0000-0000-000000000002"),
        author="Bob Jones",
        description="Second template",
        best_for=["use case 3"],
        potential_applications=["app 3"],
        query_yaml="config2: value2",
        tags=[PipelineTemplateTag(name="tag2", tag_id=UUID("20000000-0000-0000-0000-000000000002"))],
        pipeline_type=PipelineType.INDEXING,
    )
    resource = FakePipelineTemplateResource(list_response=[template1, template2])
    client = FakeClient(resource)
    result = await list_pipeline_templates(client=client, workspace="ws1")

    assert isinstance(result, PipelineTemplateList)
    assert len(result.data) == 2
    assert result.data[0].template_name == "template1"
    assert result.data[1].template_name == "template2"
    assert result.data[0].author == "Alice Smith"
    assert result.data[1].author == "Bob Jones"


@pytest.mark.asyncio
async def test_list_pipeline_templates_handles_resource_not_found() -> None:
    resource = FakePipelineTemplateResource(list_exception=ResourceNotFoundError())
    client = FakeClient(resource)
    result = await list_pipeline_templates(client=client, workspace="invalid_ws")

    assert isinstance(result, str)
    assert "no workspace named 'invalid_ws'" in result.lower()


@pytest.mark.asyncio
async def test_list_pipeline_templates_handles_unexpected_error() -> None:
    resource = FakePipelineTemplateResource(list_exception=UnexpectedAPIError(status_code=500, message="Server error"))
    client = FakeClient(resource)
    result = await list_pipeline_templates(client=client, workspace="ws1")

    assert "Failed to list pipeline templates" in result
    assert "Server error" in result


@pytest.mark.asyncio
async def test_get_pipeline_template_returns_template() -> None:
    template = PipelineTemplate(
        pipeline_name="test_template",
        name="test_template",
        pipeline_template_id=UUID("00000000-0000-0000-0000-000000000001"),
        author="Eve Brown",
        description="Test template",
        best_for=["use case 1"],
        potential_applications=["app 1"],
        query_yaml="config: value",
        tags=[PipelineTemplateTag(name="tag1", tag_id=UUID("10000000-0000-0000-0000-000000000001"))],
        pipeline_type=PipelineType.QUERY,
    )
    resource = FakePipelineTemplateResource(get_response=template)
    client = FakeClient(resource)
    result = await get_pipeline_template(client=client, workspace="ws1", template_name="test_template")

    assert isinstance(result, PipelineTemplate)
    assert result.template_name == "test_template"
    assert result.author == "Eve Brown"
    assert result.description == "Test template"
    assert result.yaml_config == "config: value"
    assert result.tags[0].name == "tag1"


@pytest.mark.asyncio
async def test_get_pipeline_template_handles_resource_not_found() -> None:
    resource = FakePipelineTemplateResource(get_exception=ResourceNotFoundError())
    client = FakeClient(resource)
    result = await get_pipeline_template(client=client, workspace="ws1", template_name="invalid_template")

    assert isinstance(result, str)
    assert "no pipeline template named 'invalid_template'" in result.lower()


@pytest.mark.asyncio
async def test_get_pipeline_template_handles_unexpected_error() -> None:
    resource = FakePipelineTemplateResource(get_exception=UnexpectedAPIError(status_code=500, message="Server error"))
    client = FakeClient(resource)
    result = await get_pipeline_template(client=client, workspace="ws1", template_name="test_template")

    assert "Failed to fetch pipeline template 'test_template'" in result
    assert "Server error" in result


@pytest.mark.asyncio
async def test_list_pipeline_templates_with_filter() -> None:
    """Test that filter parameter is passed correctly to the resource."""
    template = PipelineTemplate(
        pipeline_name="query_template",
        name="query_template",
        pipeline_template_id=UUID("00000000-0000-0000-0000-000000000001"),
        author="Test Author",
        description="A query template",
        best_for=["use case 1"],
        potential_applications=["app 1"],
        query_yaml="config: value",
        tags=[PipelineTemplateTag(name="tag1", tag_id=UUID("10000000-0000-0000-0000-000000000001"))],
        pipeline_type=PipelineType.QUERY,
    )

    resource = FakePipelineTemplateResource(list_response=[template])
    client = FakeClient(resource)

    filter_value = "pipeline_type eq 'QUERY'"
    await list_pipeline_templates(client=client, workspace="ws1", filter=filter_value)

    # Verify the filter was passed to the resource
    assert resource.last_list_call_params["filter"] == filter_value


@pytest.mark.asyncio
async def test_list_pipeline_templates_with_custom_sorting() -> None:
    """Test that custom sorting parameters are passed correctly."""
    template = PipelineTemplate(
        pipeline_name="test_template",
        name="test_template",
        pipeline_template_id=UUID("00000000-0000-0000-0000-000000000001"),
        author="Test Author",
        description="A test template",
        best_for=["use case 1"],
        potential_applications=["app 1"],
        query_yaml="config: value",
        tags=[PipelineTemplateTag(name="tag1", tag_id=UUID("10000000-0000-0000-0000-000000000001"))],
        pipeline_type=PipelineType.QUERY,
    )
    resource = FakePipelineTemplateResource(list_response=[template])
    client = FakeClient(resource)

    await list_pipeline_templates(client=client, workspace="ws1", limit=50, field="name", order="ASC")

    # Verify parameters were passed correctly
    assert resource.last_list_call_params["limit"] == 50
    assert resource.last_list_call_params["field"] == "name"
    assert resource.last_list_call_params["order"] == "ASC"
    assert resource.last_list_call_params["filter"] is None


@pytest.mark.asyncio
async def test_list_pipeline_templates_with_filter_and_sorting() -> None:
    """Test that both filter and sorting parameters work together."""
    template = PipelineTemplate(
        pipeline_name="query_template",
        name="query_template",
        pipeline_template_id=UUID("00000000-0000-0000-0000-000000000001"),
        author="Test Author",
        description="A query template",
        best_for=["use case 1"],
        potential_applications=["app 1"],
        query_yaml="config: value",
        tags=[PipelineTemplateTag(name="tag1", tag_id=UUID("10000000-0000-0000-0000-000000000001"))],
        pipeline_type=PipelineType.QUERY,
    )
    resource = FakePipelineTemplateResource(list_response=[template])
    client = FakeClient(resource)

    filter_value = "tags/any(tag: tag/name eq 'category:basic qa') and pipeline_type eq 'QUERY'"

    await list_pipeline_templates(
        client=client, workspace="ws1", limit=25, field="name", order="ASC", filter=filter_value
    )

    # Verify all parameters were passed correctly
    assert resource.last_list_call_params["limit"] == 25
    assert resource.last_list_call_params["field"] == "name"
    assert resource.last_list_call_params["order"] == "ASC"
    assert resource.last_list_call_params["filter"] == filter_value


@pytest.mark.asyncio
async def test_search_pipeline_templates_success() -> None:
    # Create sample pipeline templates
    templates = [
        PipelineTemplate(
            author="Deepset",
            best_for=["Document Q&A"],
            description="A retrieval-augmented generation template for answering questions",
            pipeline_name="rag-pipeline",
            name="RAG Pipeline",
            pipeline_template_id=uuid4(),
            potential_applications=["FAQ systems", "Document search"],
            query_yaml="components:\n  retriever: ...\n  generator: ...",
            tags=[],
            pipeline_type=PipelineType.QUERY,
        ),
        PipelineTemplate(
            author="Deepset",
            best_for=["Conversational AI"],
            description="A chat-based conversational pipeline for interactive responses",
            pipeline_name="chat-pipeline",
            name="Chat Pipeline",
            pipeline_template_id=uuid4(),
            potential_applications=["Chatbots", "Virtual assistants"],
            query_yaml="components:\n  chat_generator: ...\n  memory: ...",
            tags=[],
            pipeline_type=PipelineType.QUERY,
        ),
    ]

    resource = FakePipelineTemplateResource(list_response=templates)
    client = FakeClient(resource)
    model = FakeModel()

    # Search for RAG templates
    result = await search_pipeline_templates(
        client=client, query="retrieval augmented generation", model=model, workspace="test_workspace"
    )
    assert isinstance(result, PipelineTemplateSearchResults)
    assert result.query == "retrieval augmented generation"
    assert result.total_found == 2
    assert len(result.results) == 2
    # RAG pipeline should be first due to higher similarity
    assert result.results[0].template.template_name == "rag-pipeline"
    assert result.results[1].template.template_name == "chat-pipeline"

    # Search for chat templates
    result = await search_pipeline_templates(
        client=client, query="conversational chat interface", model=model, workspace="test_workspace"
    )
    assert isinstance(result, PipelineTemplateSearchResults)
    assert result.query == "conversational chat interface"
    assert result.total_found == 2
    assert len(result.results) == 2
    # Chat pipeline should be first due to higher similarity
    assert result.results[0].template.template_name == "chat-pipeline"
    assert result.results[1].template.template_name == "rag-pipeline"


@pytest.mark.asyncio
async def test_search_pipeline_templates_no_templates() -> None:
    resource = FakePipelineTemplateResource(list_response=[])
    client = FakeClient(resource)
    model = FakeModel()

    result = await search_pipeline_templates(client=client, query="test query", model=model, workspace="test_workspace")
    assert isinstance(result, PipelineTemplateSearchResults)
    assert result.query == "test query"
    assert result.total_found == 0
    assert len(result.results) == 0


@pytest.mark.asyncio
async def test_search_pipeline_templates_api_error() -> None:
    resource = FakePipelineTemplateResource(list_exception=UnexpectedAPIError(status_code=500, message="API Error"))
    client = FakeClient(resource)
    model = FakeModel()

    result = await search_pipeline_templates(client=client, query="test query", model=model, workspace="test_workspace")
    assert "Failed to retrieve pipeline templates" in result
