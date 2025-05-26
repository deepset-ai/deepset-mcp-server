from typing import Any
from uuid import uuid4

import numpy as np
import pytest

from deepset_mcp.api.exceptions import UnexpectedAPIError
from deepset_mcp.tools.haystack_service import (
    get_component_definition,
    list_component_families,
    search_component_definition,
)
from deepset_mcp.tools.model_protocol import ModelProtocol

from test.unit.conftest import BaseFakeClient


class FakeModel(ModelProtocol):
    def encode(self, sentences: list[str] | str) -> np.ndarray[Any, Any]:
        # Convert input to list if it's a single string
        if isinstance(sentences, str):
            sentences = [sentences]

        # Create fake embeddings with consistent similarities
        embeddings = np.zeros((len(sentences), 3))
        for i, sentence in enumerate(sentences):
            if "converter" in sentence.lower():
                embeddings[i] = [0, 0, 0.9]
            elif "reader" in sentence.lower():
                embeddings[i] = [0, 1, 0]
            elif "rag" in sentence.lower() or "retrieval" in sentence.lower():
                embeddings[i] = [1, 0, 0]
            elif "chat" in sentence.lower() or "conversation" in sentence.lower():
                embeddings[i] = [0.8, 0.2, 0]
            else:
                embeddings[i] = [0, 0, 1]
        return embeddings


class FakePipelineTemplatesResource:
    def __init__(
        self,
        list_templates_response: list[PipelineTemplate] | None = None,
        exception: Exception | None = None,
    ):
        self._list_templates_response = list_templates_response
        self._exception = exception

    async def list_templates(
        self, limit: int = 100, field: str = "created_at", order: str = "DESC", filter: str | None = None
    ) -> list[PipelineTemplate]:
        if self._exception:
            raise self._exception
        if self._list_templates_response is not None:
            return self._list_templates_response
        raise NotImplementedError


class FakeHaystackServiceResource:
    def __init__(
        self,
        get_component_schemas_response: dict[str, Any] | None = None,
        get_component_io_response: dict[str, Any] | None = None,
        exception: Exception | None = None,
    ):
        self._get_component_schemas_response = get_component_schemas_response
        self._get_component_io_response = get_component_io_response
        self._exception = exception

    async def get_component_schemas(self) -> dict[str, Any]:
        if self._exception:
            raise self._exception
        if self._get_component_schemas_response is not None:
            return self._get_component_schemas_response
        raise NotImplementedError

    async def get_component_input_output(self, component_name: str) -> dict[str, Any]:
        if self._exception:
            raise self._exception
        if self._get_component_io_response is not None:
            return self._get_component_io_response
        raise NotImplementedError


class FakeClient(BaseFakeClient):
    def __init__(
        self,
        resource: FakeHaystackServiceResource | None = None,
        templates_resource: FakePipelineTemplatesResource | None = None,
    ):
        self._resource = resource
        self._templates_resource = templates_resource
        super().__init__()

    def haystack_service(self) -> FakeHaystackServiceResource:
        if self._resource is None:
            raise ValueError("Haystack service resource not configured")
        return self._resource

    def pipeline_templates(self, workspace: str) -> FakePipelineTemplatesResource:
        if self._templates_resource is None:
            raise ValueError("Pipeline templates resource not configured")
        return self._templates_resource


@pytest.mark.asyncio
async def test_get_component_definition_success() -> None:
    # Sample component definition similar to the example provided
    component_type = "haystack.components.converters.xlsx.XLSXToDocument"
    schema_response: dict[str, Any] = {
        "component_schema": {
            "definitions": {
                "Components": {
                    "XLSXToDocument": {
                        "title": "XLSXToDocument",
                        "description": "Converts XLSX files into Documents.",
                        "properties": {
                            "type": {
                                "const": component_type,
                                "family": "converters",
                                "family_description": "Convert data into a format your pipeline can query.",
                            },
                            "init_parameters": {
                                "properties": {
                                    "sheet_name": {
                                        "_annotation": "typing.Union[str, int, list, None]",
                                        "description": "The name of the sheet to read.",
                                        "default": None,
                                    },
                                    "table_format": {
                                        "_annotation": "str",
                                        "description": "The format to convert the Excel file to.",
                                        "default": "csv",
                                    },
                                }
                            },
                        },
                    }
                }
            }
        }
    }

    io_response = {
        "input": {
            "properties": {
                "file_path": {"_annotation": "str", "description": "Path to the XLSX file", "type": "string"}
            },
            "required": ["file_path"],
            "type": "object",
        },
        "output": {
            "properties": {
                "documents": {
                    "_annotation": "typing.List[haystack.dataclasses.document.Document]",
                    "description": "List of documents",
                    "type": "array",
                    "items": {"$ref": "#/definitions/Document"},
                }
            },
            "required": ["documents"],
            "type": "object",
            "definitions": {
                "Document": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "The content of the document"},
                        "meta": {"type": "object", "description": "Metadata about the document"},
                    },
                    "required": ["content"],
                }
            },
        },
    }

    resource = FakeHaystackServiceResource(
        get_component_schemas_response=schema_response, get_component_io_response=io_response
    )
    client = FakeClient(resource=resource)
    result = await get_component_definition(client, component_type)

    # Check that all required information is present
    assert component_type in result
    assert "XLSXToDocument" in result
    assert "converters" in result
    assert "Convert data into a format" in result
    assert "sheet_name" in result
    assert "table_format" in result
    assert "default: csv" in result

    # Check input/output schema information
    assert "Input Schema:" in result
    assert "file_path" in result
    assert "Path to the XLSX file" in result
    assert "(required)" in result
    assert "Output Schema:" in result
    assert "List of documents" in result
    assert "documents: typing.List[haystack.dataclasses.document.Document]" in result
    assert "Definitions:" in result
    assert "Document:" in result
    assert "content: string (required)" in result
    assert "meta: object" in result


@pytest.mark.asyncio
async def test_get_component_definition_not_found() -> None:
    response: dict[str, Any] = {"component_schema": {"definitions": {"Components": {}}}}
    resource = FakeHaystackServiceResource(get_component_schemas_response=response)
    client = FakeClient(resource=resource)
    result = await get_component_definition(client, "nonexistent.component")
    assert "Component not found" in result


@pytest.mark.asyncio
async def test_search_component_definition_success() -> None:
    schema_response = {
        "component_schema": {
            "definitions": {
                "Components": {
                    "XLSXConverter": {
                        "title": "XLSXConverter",
                        "description": "Converts Excel files",
                        "properties": {
                            "type": {
                                "const": "haystack.components.converters.XLSXConverter",
                                "family": "converters",
                            },
                        },
                    },
                    "PDFReader": {
                        "title": "PDFReader",
                        "description": "Reads PDF files",
                        "properties": {
                            "type": {
                                "const": "haystack.components.readers.PDFReader",
                                "family": "readers",
                            },
                        },
                    },
                }
            }
        }
    }

    io_response = {
        "input": {"properties": {"file_path": {"type": "string"}}},
        "output": {"properties": {"text": {"type": "string"}}},
    }

    resource = FakeHaystackServiceResource(
        get_component_schemas_response=schema_response, get_component_io_response=io_response
    )
    client = FakeClient(resource=resource)
    model = FakeModel()

    # Search for converters
    result = await search_component_definition(client, "convert excel files", model)
    assert "XLSXConverter" in result
    assert "Similarity Score:" in result
    assert "haystack.components.converters.XLSXConverter" in result

    # Search for readers
    result = await search_component_definition(client, "read pdf documents", model)
    assert "PDFReader" in result
    assert "Similarity Score:" in result
    assert "haystack.components.readers.PDFReader" in result


@pytest.mark.asyncio
async def test_get_component_definition_api_error() -> None:
    resource = FakeHaystackServiceResource(exception=UnexpectedAPIError(status_code=500, message="API Error"))
    client = FakeClient(resource=resource)
    result = await get_component_definition(client, "some.component")
    assert "Failed to retrieve component definition" in result
    assert "API Error" in result


@pytest.mark.asyncio
async def test_search_component_definition_no_components() -> None:
    schema_response: dict[str, Any] = {"component_schema": {"definitions": {"Components": {}}}}
    resource = FakeHaystackServiceResource(get_component_schemas_response=schema_response)
    client = FakeClient(resource=resource)
    model = FakeModel()

    result = await search_component_definition(client, "test query", model)
    assert "No components found" in result


@pytest.mark.asyncio
async def test_search_component_definition_api_error() -> None:
    resource = FakeHaystackServiceResource(exception=UnexpectedAPIError(status_code=500, message="API Error"))
    client = FakeClient(resource=resource)
    model = FakeModel()

    result = await search_component_definition(client, "test query", model)
    assert "Failed to retrieve component schemas" in result


@pytest.mark.asyncio
async def test_list_component_families_no_families() -> None:
    response: dict[str, Any] = {"component_schema": {"definitions": {"Components": {}}}}
    resource = FakeHaystackServiceResource(get_component_schemas_response=response)
    client = FakeClient(resource=resource)
    result = await list_component_families(client)
    assert "No component families found" in result


@pytest.mark.asyncio
async def test_list_component_families_success() -> None:
    response = {
        "component_schema": {
            "definitions": {
                "Components": {
                    "Component1": {
                        "properties": {"type": {"family": "converters", "family_description": "Convert data format"}}
                    },
                    "Component2": {"properties": {"type": {"family": "readers", "family_description": "Read data"}}},
                    # Should be ignored - same family as Component1
                    "Component3": {
                        "properties": {"type": {"family": "converters", "family_description": "Convert data format"}}
                    },
                }
            }
        }
    }
    resource = FakeHaystackServiceResource(get_component_schemas_response=response)
    client = FakeClient(resource=resource)
    result = await list_component_families(client)

    assert "Available Haystack component families" in result
    assert "**converters**" in result
    assert "Convert data format" in result
    assert "**readers**" in result
    assert "Read data" in result
    # Only two unique families should be present
    assert result.count("**") == 4  # Two sets of ** for each family


@pytest.mark.asyncio
async def test_list_component_families_api_error() -> None:
    resource = FakeHaystackServiceResource(exception=UnexpectedAPIError(status_code=500, message="API Error"))
    client = FakeClient(resource=resource)
    result = await list_component_families(client)
    assert "Failed to retrieve component families" in result
    assert "API Error" in result


@pytest.mark.asyncio
async def test_search_pipeline_templates_success() -> None:
    # Create sample pipeline templates
    templates = [
        PipelineTemplate(
            author="Deepset",
            best_for=["Document Q&A"],
            description="A retrieval-augmented generation template for answering questions",
            template_name="rag-pipeline",
            display_name="RAG Pipeline",
            pipeline_template_id=uuid4(),
            potential_applications=["FAQ systems", "Document search"],
            yaml_config="components:\n  retriever: ...\n  generator: ...",
            tags=[],
            pipeline_type=PipelineType.QUERY,
        ),
        PipelineTemplate(
            author="Deepset",
            best_for=["Conversational AI"],
            description="A chat-based conversational pipeline for interactive responses",
            template_name="chat-pipeline",
            display_name="Chat Pipeline",
            pipeline_template_id=uuid4(),
            potential_applications=["Chatbots", "Virtual assistants"],
            yaml_config="components:\n  chat_generator: ...\n  memory: ...",
            tags=[],
            pipeline_type=PipelineType.QUERY,
        ),
    ]

    templates_resource = FakePipelineTemplatesResource(list_templates_response=templates)
    client = FakeClient(templates_resource=templates_resource)
    model = FakeModel()

    # Search for RAG templates
    result = await search_pipeline_templates(client, "retrieval augmented generation", model, "test_workspace")
    assert "rag-pipeline" in result
    assert "Similarity Score:" in result
    assert "retrieval-augmented generation" in result

    # Search for chat templates
    result = await search_pipeline_templates(client, "conversational chat interface", model, "test_workspace")
    assert "chat-pipeline" in result
    assert "Similarity Score:" in result
    assert "chat-based conversational" in result


@pytest.mark.asyncio
async def test_search_pipeline_templates_no_templates() -> None:
    templates_resource = FakePipelineTemplatesResource(list_templates_response=[])
    client = FakeClient(templates_resource=templates_resource)
    model = FakeModel()

    result = await search_pipeline_templates(client, "test query", model, "test_workspace")
    assert "No pipeline templates found" in result


@pytest.mark.asyncio
async def test_search_pipeline_templates_api_error() -> None:
    templates_resource = FakePipelineTemplatesResource(
        exception=UnexpectedAPIError(status_code=500, message="API Error")
    )
    client = FakeClient(templates_resource=templates_resource)
    model = FakeModel()

    result = await search_pipeline_templates(client, "test query", model, "test_workspace")
    assert "Failed to retrieve pipeline templates" in result
