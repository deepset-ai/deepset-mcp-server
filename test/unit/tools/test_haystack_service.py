from typing import Any

import pytest

from deepset_mcp.api.exceptions import UnexpectedAPIError
from deepset_mcp.tools.haystack_service import list_component_families
from test.unit.conftest import BaseFakeClient


class FakeHaystackServiceResource:
    def __init__(
        self, get_component_schemas_response: dict[str, Any] | None = None, exception: Exception | None = None
    ):
        self._get_component_schemas_response = get_component_schemas_response
        self._exception = exception

    async def get_component_schemas(self) -> dict[str, Any]:
        if self._exception:
            raise self._exception
        if self._get_component_schemas_response is not None:
            return self._get_component_schemas_response
        raise NotImplementedError


class FakeClient(BaseFakeClient):
    def __init__(self, resource: FakeHaystackServiceResource):
        self._resource = resource
        super().__init__()

    def haystack_service(self) -> FakeHaystackServiceResource:
        return self._resource


@pytest.mark.asyncio
async def test_get_component_definition_success() -> None:
    # Sample component definition similar to the example provided
    component_type = "haystack.components.converters.xlsx.XLSXToDocument"
    response = {
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
                                "family_description": "Convert data into a format your pipeline can query."
                            },
                            "init_parameters": {
                                "properties": {
                                    "sheet_name": {
                                        "_annotation": "typing.Union[str, int, list, None]",
                                        "description": "The name of the sheet to read.",
                                        "default": None
                                    },
                                    "table_format": {
                                        "_annotation": "str",
                                        "description": "The format to convert the Excel file to.",
                                        "default": "csv"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    resource = FakeHaystackServiceResource(get_component_schemas_response=response)
    client = FakeClient(resource)
    result = await get_component_definition(client, component_type)
    
    # Check that all required information is present
    assert component_type in result
    assert "XLSXToDocument" in result
    assert "converters" in result
    assert "Convert data into a format" in result
    assert "sheet_name" in result
    assert "table_format" in result
    assert "default: csv" in result


@pytest.mark.asyncio
async def test_get_component_definition_not_found() -> None:
    response = {
        "component_schema": {
            "definitions": {
                "Components": {}
            }
        }
    }
    resource = FakeHaystackServiceResource(get_component_schemas_response=response)
    client = FakeClient(resource)
    result = await get_component_definition(client, "nonexistent.component")
    assert "Component not found" in result


@pytest.mark.asyncio
async def test_get_component_definition_api_error() -> None:
    resource = FakeHaystackServiceResource(exception=UnexpectedAPIError(status_code=500, message="API Error"))
    client = FakeClient(resource)
    result = await get_component_definition(client, "some.component")
    assert "Failed to retrieve component definition" in result
    assert "API Error" in result


@pytest.mark.asyncio
async def test_list_component_families_no_families() -> None:
    response: dict[str, Any] = {"component_schema": {"definitions": {"Components": {}}}}
    resource = FakeHaystackServiceResource(get_component_schemas_response=response)
    client = FakeClient(resource)
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
    client = FakeClient(resource)
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
    client = FakeClient(resource)
    result = await list_component_families(client)
    assert "Failed to retrieve component families" in result
    assert "API Error" in result
