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
