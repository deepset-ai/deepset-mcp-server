# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any

import numpy as np
import pytest

from deepset_mcp.api.exceptions import UnexpectedAPIError
from deepset_mcp.tools.haystack_service import (
    extract_component_texts,
    get_component_definition,
    get_custom_components,
    list_component_families,
    search_component_definition,
)
from deepset_mcp.tools.haystack_service_models import (
    ComponentDefinition,
    ComponentDefinitionList,
    ComponentFamilyList,
    ComponentSearchResults,
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
    ):
        self._resource = resource
        super().__init__()

    def haystack_service(self) -> FakeHaystackServiceResource:
        if self._resource is None:
            raise ValueError("Haystack service resource not configured")
        return self._resource


def test_extract_component_texts() -> None:
    component_def = {
        "title": "TestComponent",
        "description": "A test component",
        "properties": {
            "type": {
                "const": "test.component.TestComponent",
            },
        },
    }

    component_type, text = extract_component_texts(component_def=component_def)

    assert component_type == "test.component.TestComponent"
    assert text == "TestComponent A test component"


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
                                },
                                "required": ["table_format"],
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
    result = await get_component_definition(client=client, component_type=component_type)

    # Check that we get a ComponentDefinition model
    assert isinstance(result, ComponentDefinition)
    assert result.component_type == component_type
    assert result.title == "XLSXToDocument"
    assert result.description == "Converts XLSX files into Documents."
    assert result.family == "converters"
    assert result.family_description == "Convert data into a format your pipeline can query."

    # Check init parameters
    assert len(result.init_parameters) == 2
    sheet_name_param = next((p for p in result.init_parameters if p.name == "sheet_name"), None)
    assert sheet_name_param is not None
    assert sheet_name_param.annotation == "typing.Union[str, int, list, None]"
    assert sheet_name_param.description == "The name of the sheet to read."
    assert sheet_name_param.default is None
    assert not sheet_name_param.required

    table_format_param = next((p for p in result.init_parameters if p.name == "table_format"), None)
    assert table_format_param is not None
    assert table_format_param.required

    # Check input/output schemas
    assert result.input_schema is not None
    assert "file_path" in result.input_schema.properties
    assert result.input_schema.properties["file_path"].description == "Path to the XLSX file"
    assert "file_path" in result.input_schema.required

    assert result.output_schema is not None
    assert "documents" in result.output_schema.properties
    assert result.output_schema.properties["documents"].description == "List of documents"
    assert "documents" in result.output_schema.required
    assert "Document" in result.output_schema.definitions


@pytest.mark.asyncio
async def test_get_component_definition_not_found() -> None:
    response: dict[str, Any] = {"component_schema": {"definitions": {"Components": {}}}}
    resource = FakeHaystackServiceResource(get_component_schemas_response=response)
    client = FakeClient(resource=resource)
    result = await get_component_definition(client=client, component_type="nonexistent.component")

    assert isinstance(result, str)
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
                                "family_description": "Convert data into a format your pipeline can query.",
                            },
                            "init_parameters": {"properties": {}},
                        },
                    },
                    "PDFReader": {
                        "title": "PDFReader",
                        "description": "Reads PDF files",
                        "properties": {
                            "type": {
                                "const": "haystack.components.readers.PDFReader",
                                "family": "readers",
                                "family_description": "Read and parse documents.",
                            },
                            "init_parameters": {"properties": {}},
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
    result = await search_component_definition(client=client, query="convert excel files", model=model)
    assert isinstance(result, ComponentSearchResults)
    assert result.query == "convert excel files"
    assert result.total_found == 2
    assert len(result.results) == 2
    # XLSXConverter should be first due to higher similarity
    assert result.results[0].component.title == "XLSXConverter"
    assert result.results[0].component.component_type == "haystack.components.converters.XLSXConverter"
    assert isinstance(result.results[0].similarity_score, float)

    # Search for readers
    result = await search_component_definition(client=client, query="pdf reader documents", model=model)
    assert isinstance(result, ComponentSearchResults)
    assert result.query == "pdf reader documents"
    assert result.total_found == 2
    assert len(result.results) == 2
    # PDFReader should be first due to higher similarity
    assert result.results[0].component.title == "PDFReader"
    assert result.results[0].component.component_type == "haystack.components.readers.PDFReader"


@pytest.mark.asyncio
async def test_get_component_definition_api_error() -> None:
    resource = FakeHaystackServiceResource(exception=UnexpectedAPIError(status_code=500, message="API Error"))
    client = FakeClient(resource=resource)
    result = await get_component_definition(client=client, component_type="some.component")

    assert isinstance(result, str)
    assert "Failed to retrieve component definition" in result
    assert "API Error" in result


@pytest.mark.asyncio
async def test_search_component_definition_no_components() -> None:
    schema_response: dict[str, Any] = {"component_schema": {"definitions": {"Components": {}}}}
    resource = FakeHaystackServiceResource(get_component_schemas_response=schema_response)
    client = FakeClient(resource=resource)
    model = FakeModel()

    result = await search_component_definition(client=client, query="test query", model=model)
    assert isinstance(result, ComponentSearchResults)
    assert result.query == "test query"
    assert result.total_found == 0
    assert len(result.results) == 0


@pytest.mark.asyncio
async def test_search_component_definition_api_error() -> None:
    resource = FakeHaystackServiceResource(exception=UnexpectedAPIError(status_code=500, message="API Error"))
    client = FakeClient(resource=resource)
    model = FakeModel()

    result = await search_component_definition(client=client, query="test query", model=model)
    assert isinstance(result, str)
    assert "Failed to retrieve component schemas" in result


@pytest.mark.asyncio
async def test_list_component_families_no_families() -> None:
    response: dict[str, Any] = {"component_schema": {"definitions": {"Components": {}}}}
    resource = FakeHaystackServiceResource(get_component_schemas_response=response)
    client = FakeClient(resource=resource)
    result = await list_component_families(client=client)

    assert isinstance(result, str)
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
    result = await list_component_families(client=client)

    assert isinstance(result, ComponentFamilyList)
    assert result.total_count == 2
    assert len(result.families) == 2

    # Check sorted order
    families_by_name = {f.name: f for f in result.families}
    assert "converters" in families_by_name
    assert families_by_name["converters"].description == "Convert data format"
    assert "readers" in families_by_name
    assert families_by_name["readers"].description == "Read data"


@pytest.mark.asyncio
async def test_list_component_families_api_error() -> None:
    resource = FakeHaystackServiceResource(exception=UnexpectedAPIError(status_code=500, message="API Error"))
    client = FakeClient(resource=resource)
    result = await list_component_families(client=client)

    assert isinstance(result, str)
    assert "Failed to retrieve component families" in result
    assert "API Error" in result


@pytest.mark.asyncio
async def test_get_custom_components_success() -> None:
    response = {
        "component_schema": {
            "definitions": {
                "Components": {
                    "CustomComponent1": {
                        "title": "CustomComponent1",
                        "description": "A custom component for testing",
                        "package_version": "1.0.0",
                        "dynamic_params": True,
                        "properties": {
                            "type": {
                                "const": "custom.components.CustomComponent1",
                                "family": "custom",
                                "family_description": "Custom components",
                            },
                            "init_parameters": {
                                "properties": {
                                    "param1": {
                                        "_annotation": "str",
                                        "description": "First parameter",
                                    },
                                    "param2": {
                                        "_annotation": "int",
                                        "description": "Second parameter",
                                    },
                                },
                                "required": ["param1"],
                            },
                        },
                    },
                    "RegularComponent": {
                        # No package_version, so not a custom component
                        "title": "RegularComponent",
                        "description": "A regular component",
                        "properties": {
                            "type": {
                                "const": "haystack.components.RegularComponent",
                                "family": "regular",
                                "family_description": "Regular components",
                            },
                            "init_parameters": {"properties": {}},
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
        get_component_schemas_response=response, get_component_io_response=io_response
    )
    client = FakeClient(resource=resource)
    result = await get_custom_components(client=client)

    assert isinstance(result, ComponentDefinitionList)
    assert result.total_count == 1
    assert len(result.components) == 1

    custom_comp = result.components[0]
    assert custom_comp.title == "CustomComponent1"
    assert custom_comp.component_type == "custom.components.CustomComponent1"
    assert custom_comp.package_version == "1.0.0"
    assert custom_comp.family == "custom"
    assert custom_comp.family_description == "Custom components"
    assert custom_comp.dynamic_params is True
    assert custom_comp.is_custom is True
    assert len(custom_comp.init_parameters) == 2

    # Check parameters
    param1 = next((p for p in custom_comp.init_parameters if p.name == "param1"), None)
    assert param1 is not None
    assert param1.annotation == "str"
    assert param1.description == "First parameter"
    assert param1.required is True

    param2 = next((p for p in custom_comp.init_parameters if p.name == "param2"), None)
    assert param2 is not None
    assert param2.annotation == "int"
    assert param2.description == "Second parameter"
    assert param2.required is False

    # Check I/O schemas are included
    assert custom_comp.input_schema is not None
    assert custom_comp.output_schema is not None


@pytest.mark.asyncio
async def test_get_custom_components_none_found() -> None:
    response = {
        "component_schema": {
            "definitions": {
                "Components": {
                    "RegularComponent": {
                        "title": "RegularComponent",
                        "description": "A regular component",
                        "properties": {
                            "type": {
                                "const": "haystack.components.RegularComponent",
                                "family": "regular",
                                "family_description": "Regular components",
                            },
                            "init_parameters": {"properties": {}},
                        },
                    }
                }
            }
        }
    }
    resource = FakeHaystackServiceResource(get_component_schemas_response=response)
    client = FakeClient(resource=resource)
    result = await get_custom_components(client=client)

    assert isinstance(result, str)
    assert "No custom components found" in result


@pytest.mark.asyncio
async def test_get_custom_components_api_error() -> None:
    resource = FakeHaystackServiceResource(exception=UnexpectedAPIError(status_code=500, message="API Error"))
    client = FakeClient(resource=resource)
    result = await get_custom_components(client=client)

    assert isinstance(result, str)
    assert "Error retrieving component schemas" in result
    assert "API Error" in result
