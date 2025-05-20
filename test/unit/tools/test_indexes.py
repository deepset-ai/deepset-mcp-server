from typing import AsyncGenerator, Callable

import pytest
from pytest_mock import MockFixture

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.indexes.models import Index, IndexList
from deepset_mcp.api.protocols import AsyncClientProtocol, IndexResourceProtocol
from deepset_mcp.tools.indexes import create_index, get_index, list_indexes, update_index
from test.unit.conftest import BaseFakeClient


class FakeIndexResource(IndexResourceProtocol):
    def __init__(self, mocker: MockFixture):
        self._mocker = mocker
        self._list = self._mocker.AsyncMock(return_value=IndexList(data=[]))
        self._get = self._mocker.AsyncMock(
            return_value=Index(
                name="test_index",
                config_yaml="config",
                id="123",
                description="Test index",
            )
        )
        self._create = self._mocker.AsyncMock(
            return_value=Index(
                name="test_index",
                config_yaml="config",
                id="123",
                description="Test index",
            )
        )
        self._update = self._mocker.AsyncMock()

    async def list(self, limit: int = 10, page_number: int = 1) -> IndexList:
        return await self._list(limit=limit, page_number=page_number)

    async def get(self, index_name: str) -> Index:
        return await self._get(index_name=index_name)

    async def create(self, name: str, yaml_config: str, description: str | None = None) -> Index:
        return await self._create(name=name, yaml_config=yaml_config, description=description)

    async def update(
        self, index_name: str, updated_index_name: str | None = None, yaml_config: str | None = None
    ) -> None:
        await self._update(index_name=index_name, updated_index_name=updated_index_name, yaml_config=yaml_config)


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
    mocker: MockFixture,
    error_class: type[Exception],
    expected_message: str,
) -> None:
    fake_resource: IndexResourceProtocol = client.indexes(workspace="test")
    assert isinstance(fake_resource, FakeIndexResource)
    fake_resource._create.side_effect = error_class("Error")

    result = await create_index(
        client=client,
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
    mocker: MockFixture,
    error_class: type[Exception],
    expected_message: str,
) -> None:
    fake_resource: IndexResourceProtocol = client.indexes(workspace="test")
    assert isinstance(fake_resource, FakeIndexResource)
    fake_resource._update.side_effect = error_class("Error")

    result = await update_index(
        client=client,
        workspace="test",
        index_name="test_index",
        updated_index_name="new_test_index",
        yaml_configuration="new_config",
    )

    assert expected_message in result