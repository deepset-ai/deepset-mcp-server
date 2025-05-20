from typing import AsyncGenerator, Callable

import pytest
from pytest_mock import MockFixture

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.indexes.models import Index, IndexList
from deepset_mcp.api.protocols import AsyncClientProtocol, IndexResourceProtocol
from deepset_mcp.tools.indexes import create_index, get_index, list_indexes, update_index
from test.unit.conftest import BaseFakeClient


class FakeIndexResource(IndexResourceProtocol):
    def __init__(
        self,
        list_response: IndexList | None = None,
        get_response: Index | None = None,
        create_response: Index | None = None,
        get_exception: Exception | None = None,
        create_exception: Exception | None = None,
        update_exception: Exception | None = None,
    ) -> None:
        self._list_response = list_response or IndexList(data=[])
        self._get_response = get_response or Index(
            name="test_index",
            config_yaml="config",
            id="123",
            description="Test index",
        )
        self._create_response = create_response
        self._get_exception = get_exception
        self._create_exception = create_exception
        self._update_exception = update_exception

    async def list(self, limit: int = 10, page_number: int = 1) -> IndexList:
        return self._list_response

    async def get(self, index_name: str) -> Index:
        if self._get_exception:
            raise self._get_exception
        return self._get_response

    async def create(self, name: str, yaml_config: str, description: str | None = None) -> Index:
        if self._create_exception:
            raise self._create_exception
        if self._create_response is not None:
            return self._create_response
        return Index(
            name=name,
            config_yaml=yaml_config,
            id="123",
            description=description,
        )

    async def update(
        self, index_name: str, updated_index_name: str | None = None, yaml_config: str | None = None
    ) -> None:
        if self._update_exception:
            raise self._update_exception


@pytest.fixture(name="client")
def client_fixture() -> AsyncGenerator[AsyncClientProtocol, None]:
    class FakeClient(BaseFakeClient):
        def indexes(self, workspace: str) -> IndexResourceProtocol:
            return FakeIndexResource()

    c = FakeClient()
    return c


PYTEST_TUPLE = tuple[AsyncClientProtocol, MockFixture]


@pytest.mark.asyncio
async def test_list_indexes_returns_formatted_string_when_no_indexes(client: AsyncClientProtocol) -> None:
    result = await list_indexes(client=client, workspace="test")

    assert result == "No indexes found."


@pytest.mark.asyncio
async def test_list_indexes_returns_formatted_string_with_indexes(
    client: AsyncClientProtocol
) -> None:
    index = Index(name="test_index", config_yaml="config", id="123", description="Test index")
    c = FakeClient()
    c._indexes = FakeIndexResource(list_response=IndexList(data=[index]))
    
    result = await list_indexes(client=c, workspace="test")

    assert "test_index" in result
    assert "config" in result
    assert "123" in result 
    assert "Test index" in result


@pytest.mark.asyncio
async def test_get_index_returns_formatted_string(
    client: AsyncClientProtocol, mocker: MockFixture
) -> None:
    result = await get_index(client=client, workspace="test", index_name="test_index")

    assert "test_index" in result
    assert "config" in result
    assert "123" in result
    assert "Test index" in result


@pytest.mark.asyncio
async def test_get_index_returns_error_message_when_index_not_found(
    client: AsyncClientProtocol, mocker: MockFixture
) -> None:
    fake_resource: IndexResourceProtocol = client.indexes(workspace="test")
    assert isinstance(fake_resource, FakeIndexResource)
    fake_resource._get.side_effect = ResourceNotFoundError("Not found")

    result = await get_index(client=client, workspace="test", index_name="test_index")

    assert "There is no index named 'test_index'" in result


@pytest.mark.asyncio
async def test_create_index_returns_success_message(
    client: AsyncClientProtocol, mocker: MockFixture
) -> None:
    result = await create_index(
        client=client,
        workspace="test",
        index_name="test_index",
        yaml_configuration="config",
        description="Test index",
    )

    assert "Index 'test_index' created successfully." == result


@pytest.mark.parametrize(
    "error_class,expected_message",
    [
        (ResourceNotFoundError, "There is no workspace named 'test'"),
        (BadRequestError, "Failed to create index 'test_index'"),
        (UnexpectedAPIError, "Failed to create index 'test_index'"),
    ],
)
async def test_create_index_returns_error_message(
    client: AsyncClientProtocol,
    error_class: type[Exception],
    expected_message: str,
) -> None:
    c = FakeClient()
    c._indexes = FakeIndexResource(create_exception=error_class("Error"))

    result = await create_index(
        client=c,
        workspace="test",
        index_name="test_index",
        yaml_configuration="config",
        description="Test index",
    )

    assert expected_message in result


@pytest.mark.asyncio
async def test_update_index_returns_success_message(
    client: AsyncClientProtocol, mocker: MockFixture
) -> None:
    result = await update_index(
        client=client,
        workspace="test",
        index_name="test_index",
        updated_index_name="new_test_index",
        yaml_configuration="new_config",
    )

    assert "Index 'test_index' updated successfully." == result


@pytest.mark.asyncio
async def test_update_index_returns_error_message_when_no_changes_provided(
    client: AsyncClientProtocol, mocker: MockFixture
) -> None:
    result = await update_index(
        client=client,
        workspace="test",
        index_name="test_index",
    )

    assert "You must provide either a new name or a new configuration to update the index." == result


@pytest.mark.parametrize(
    "error_class,expected_message",
    [
        (ResourceNotFoundError, "There is no index named 'test_index'"),
        (BadRequestError, "Failed to update index 'test_index'"),
        (UnexpectedAPIError, "Failed to update index 'test_index'"),
    ],
)
async def test_update_index_returns_error_message(
    client: AsyncClientProtocol,
    error_class: type[Exception],
    expected_message: str,
) -> None:
    c = FakeClient()
    c._indexes = FakeIndexResource(update_exception=error_class("Error"))

    result = await update_index(
        client=c,
        workspace="test",
        index_name="test_index",
        updated_index_name="new_test_index",
        yaml_configuration="new_config",
    )

    assert expected_message in result