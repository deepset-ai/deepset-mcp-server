from datetime import datetime

import pytest

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.indexes.models import Index, IndexList, IndexStatus
from deepset_mcp.api.protocols import IndexResourceProtocol
from deepset_mcp.api.shared_models import DeepsetUser
from deepset_mcp.tools.indexes import create_index, get_index, list_indexes, update_index
from test.unit.conftest import BaseFakeClient


class FakeIndexResource(IndexResourceProtocol):
    def __init__(
        self,
        list_response: IndexList | None = None,
        get_response: Index | None = None,
        create_response: Index | None = None,
        update_response: Index | None = None,
        get_exception: Exception | None = None,
        create_exception: Exception | None = None,
        update_exception: Exception | None = None,
    ) -> None:
        self._list_response = list_response
        self._get_response = get_response
        self._create_response = create_response
        self._update_response = update_response
        self._get_exception = get_exception
        self._create_exception = create_exception
        self._update_exception = update_exception

    async def list(self, limit: int = 10, page_number: int = 1) -> IndexList:
        if self._list_response is not None:
            return self._list_response
        return IndexList(data=[], has_more=False, total=0)

    async def get(self, index_name: str) -> Index:
        if self._get_exception:
            raise self._get_exception
        if self._get_response is not None:
            return self._get_response
        raise NotImplementedError

    async def create(self, name: str, yaml_config: str, description: str | None = None) -> Index:
        if self._create_exception:
            raise self._create_exception
        if self._create_response is not None:
            return self._create_response
        raise NotImplementedError

    async def update(
        self, index_name: str, updated_index_name: str | None = None, yaml_config: str | None = None
    ) -> Index:
        if self._update_exception:
            raise self._update_exception
        if self._update_response is not None:
            return self._update_response

        raise NotImplementedError


class FakeClient(BaseFakeClient):
    def __init__(self, resource: FakeIndexResource) -> None:
        self._resource = resource
        super().__init__()

    def indexes(self, workspace: str) -> FakeIndexResource:
        return self._resource


def create_test_index(
    name: str = "test_index",
    description: str | None = "Test index description",
    config_yaml: str = "config: value",
) -> Index:
    """Helper function to create a complete Index object for testing."""
    user = DeepsetUser(user_id="u1", given_name="Test", family_name="User")
    status = IndexStatus(
        pending_file_count=0,
        failed_file_count=0,
        indexed_no_documents_file_count=0,
        indexed_file_count=10,
        total_file_count=10,
    )

    return Index(
        pipeline_index_id="idx_123",
        name=name,
        description=description,
        config_yaml=config_yaml,
        workspace_id="ws_123",
        settings={"key": "value"},
        desired_status="DEPLOYED",
        deployed_at=datetime(2023, 1, 1, 12, 0),
        last_edited_at=datetime(2023, 1, 2, 14, 30),
        max_index_replica_count=3,
        created_at=datetime(2023, 1, 1, 10, 0),
        updated_at=datetime(2023, 1, 2, 14, 30),
        created_by=user,
        last_edited_by=user,
        status=status,
    )


@pytest.mark.asyncio
async def test_list_indexes_returns_formatted_string_when_no_indexes() -> None:
    resource = FakeIndexResource(list_response=IndexList(data=[], has_more=False, total=0))
    client = FakeClient(resource)

    result = await list_indexes(client=client, workspace="test")

    assert result == "No indexes found."


@pytest.mark.asyncio
async def test_list_indexes_returns_formatted_string_with_indexes() -> None:
    index1 = create_test_index(name="index1", description="First index")
    index2 = create_test_index(name="index2", description="Second index")

    resource = FakeIndexResource(list_response=IndexList(data=[index1, index2], has_more=False, total=2))
    client = FakeClient(resource)

    result = await list_indexes(client=client, workspace="test")

    assert "index1" in result
    assert "index2" in result
    assert "First index" in result
    assert "Second index" in result
    assert "idx_123" in result


@pytest.mark.asyncio
async def test_get_index_returns_formatted_string() -> None:
    index = create_test_index(name="my_index", description="My special index")
    resource = FakeIndexResource(get_response=index)
    client = FakeClient(resource)

    result = await get_index(client=client, workspace="test", index_name="my_index")

    assert "my_index" in result
    assert "config: value" in result
    assert "idx_123" in result
    assert "My special index" in result


@pytest.mark.asyncio
async def test_get_index_returns_error_message_when_index_not_found() -> None:
    resource = FakeIndexResource(get_exception=ResourceNotFoundError())
    client = FakeClient(resource)

    result = await get_index(client=client, workspace="test", index_name="nonexistent")

    assert "There is no index named 'nonexistent'" in result


@pytest.mark.asyncio
async def test_create_index_returns_success_message() -> None:
    created_index = create_test_index(name="new_index")
    resource = FakeIndexResource(create_response=created_index)
    client = FakeClient(resource)

    result = await create_index(
        client=client,
        workspace="test",
        index_name="new_index",
        yaml_configuration="config: new",
        description="New index description",
    )

    assert "Index 'new_index' created successfully." == result


@pytest.mark.parametrize(
    "error_class,expected_message",
    [
        (ResourceNotFoundError, "There is no workspace named 'test'"),
        (BadRequestError, "Failed to create index 'test_index'"),
        (UnexpectedAPIError, "Failed to create index 'test_index'"),
    ],
)
@pytest.mark.asyncio
async def test_create_index_returns_error_message(
    error_class: type[Exception],
    expected_message: str,
) -> None:
    resource = FakeIndexResource(create_exception=error_class("Error message"))
    client = FakeClient(resource)

    result = await create_index(
        client=client,
        workspace="test",
        index_name="test_index",
        yaml_configuration="config",
        description="Test index",
    )

    assert expected_message in result


@pytest.mark.asyncio
async def test_update_index_returns_success_message() -> None:
    resource = FakeIndexResource(update_response=create_test_index(name="new_test_index"))
    client = FakeClient(resource)

    result = await update_index(
        client=client,
        workspace="test",
        index_name="test_index",
        updated_index_name="new_test_index",
        yaml_configuration="new_config",
    )

    assert "Index 'test_index' updated successfully." == result


@pytest.mark.asyncio
async def test_update_index_returns_error_message_when_no_changes_provided() -> None:
    resource = FakeIndexResource()
    client = FakeClient(resource)

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
@pytest.mark.asyncio
async def test_update_index_returns_error_message(
    error_class: type[Exception],
    expected_message: str,
) -> None:
    resource = FakeIndexResource(update_exception=error_class("Error details"))
    client = FakeClient(resource)

    result = await update_index(
        client=client,
        workspace="test",
        index_name="test_index",
        updated_index_name="new_test_index",
        yaml_configuration="new_config",
    )

    assert expected_message in result


@pytest.mark.asyncio
async def test_get_index_raises_unexpected_api_error() -> None:
    resource = FakeIndexResource(get_exception=UnexpectedAPIError(status_code=500, message="Server error"))
    client = FakeClient(resource)

    with pytest.raises(UnexpectedAPIError):
        await get_index(client=client, workspace="test", index_name="test_index")


@pytest.mark.asyncio
async def test_create_index_with_detailed_error_messages() -> None:
    # Test BadRequestError with detailed message
    resource_bad = FakeIndexResource(create_exception=BadRequestError(message="Invalid YAML configuration"))
    client_bad = FakeClient(resource_bad)

    result_bad = await create_index(
        client=client_bad,
        workspace="test",
        index_name="bad_index",
        yaml_configuration="invalid",
    )

    assert "Failed to create index 'bad_index'" in result_bad
    assert "Invalid YAML configuration" in result_bad
    assert "400" in result_bad

    # Test UnexpectedAPIError with status code
    resource_unexpected = FakeIndexResource(
        create_exception=UnexpectedAPIError(status_code=503, message="Service unavailable")
    )
    client_unexpected = FakeClient(resource_unexpected)

    result_unexpected = await create_index(
        client=client_unexpected,
        workspace="test",
        index_name="unavailable_index",
        yaml_configuration="config",
    )

    assert "Failed to create index 'unavailable_index'" in result_unexpected
    assert "Service unavailable" in result_unexpected
    assert "503" in result_unexpected


@pytest.mark.asyncio
async def test_update_index_with_detailed_error_messages() -> None:
    # Test with detailed BadRequestError
    resource = FakeIndexResource(update_exception=BadRequestError(message="Name already exists"))
    client = FakeClient(resource)

    result = await update_index(
        client=client,
        workspace="test",
        index_name="existing_index",
        updated_index_name="duplicate_name",
    )

    assert "Failed to update index 'existing_index'" in result
    assert "Name already exists" in result
    assert "400" in result
