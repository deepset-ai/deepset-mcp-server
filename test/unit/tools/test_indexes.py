# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0


import pytest

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.indexes.models import Index
from deepset_mcp.api.indexes.protocols import IndexResourceProtocol
from deepset_mcp.api.pipeline.models import PipelineValidationResult, ValidationError
from deepset_mcp.api.shared_models import PaginatedResponse
from deepset_mcp.tools.indexes import (
    IndexValidationResultWithYaml,
    create_index,
    deploy_index,
    get_index,
    list_indexes,
    update_index,
    validate_index,
)
from test.unit.conftest import BaseFakeClient


class FakeIndexResource(IndexResourceProtocol):
    def __init__(
        self,
        list_response: PaginatedResponse[Index] | None = None,
        get_response: Index | None = None,
        get_responses: list[Index] | None = None,  # For sequential responses during waiting
        create_response: Index | None = None,
        update_response: Index | None = None,
        validate_response: PipelineValidationResult | None = None,
        deploy_response: PipelineValidationResult | None = None,
        list_exception: Exception | None = None,
        get_exception: Exception | None = None,
        create_exception: Exception | None = None,
        update_exception: Exception | None = None,
        validate_exception: Exception | None = None,
        deploy_exception: Exception | None = None,
    ) -> None:
        self._list_response = list_response
        self._get_response = get_response
        self._get_responses = get_responses or []
        self._get_call_count = 0
        self._create_response = create_response
        self._update_response = update_response
        self._validate_response = validate_response
        self._deploy_response = deploy_response
        self._list_exception = list_exception
        self._get_exception = get_exception
        self._create_exception = create_exception
        self._update_exception = update_exception
        self._validate_exception = validate_exception
        self._deploy_exception = deploy_exception

    async def list(self, limit: int = 10, after: str | None = None) -> PaginatedResponse[Index]:
        if self._list_exception:
            raise self._list_exception
        if self._list_response is not None:
            return self._list_response
        return PaginatedResponse(data=[], has_more=False, total=0)

    async def get(self, index_name: str) -> Index:
        if self._get_exception:
            raise self._get_exception

        # If we have multiple responses for sequential calls (used for update tests)
        if self._get_responses:
            if self._get_call_count < len(self._get_responses):
                response = self._get_responses[self._get_call_count]
                self._get_call_count += 1
                return response
            else:
                # Return the last response if we've exhausted the list
                return self._get_responses[-1]

        if self._get_response is not None:
            return self._get_response
        raise NotImplementedError

    async def create(self, index_name: str, yaml_config: str, description: str | None = None) -> Index:
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

    async def deploy(self, index_name: str) -> PipelineValidationResult:
        if self._deploy_exception:
            raise self._deploy_exception
        if self._deploy_response is not None:
            return self._deploy_response
        return PipelineValidationResult(valid=True)

    async def validate(self, yaml_config: str) -> PipelineValidationResult:
        if self._validate_exception:
            raise self._validate_exception
        if self._validate_response is not None:
            return self._validate_response
        raise NotImplementedError

    async def delete(self, index_name: str) -> None:
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
    yaml_config: str = "config: value",
) -> Index:
    """Helper function to create a complete Index object for testing."""

    return Index.model_validate(
        {
            "pipeline_index_id": "idx_123",
            "name": name,
            "description": description,
            "config_yaml": yaml_config,
            "workspace_id": "ws_123",
            "settings": {"key": "value"},
            "desired_status": "DEPLOYED",
            "deployed_at": "2023-01-01T12:00:00Z",
            "last_edited_at": "2023-01-02T14:30:00Z",
            "max_index_replica_count": 3,
            "created_at": "2023-01-01T10:00:00Z",
            "updated_at": "2023-01-02T14:30:00Z",
            "created_by": {"user_id": "u1", "given_name": "Test", "family_name": "User"},
            "last_edited_by": {"user_id": "u1", "given_name": "Test", "family_name": "User"},
            "status": {
                "pending_file_count": 0,
                "failed_file_count": 0,
                "indexed_no_documents_file_count": 0,
                "indexed_file_count": 10,
                "total_file_count": 10,
            },
        }
    )


@pytest.mark.asyncio
async def test_list_indexes_without_indexes() -> None:
    resource = FakeIndexResource(list_response=PaginatedResponse(data=[], has_more=False, total=0))
    client = FakeClient(resource)

    result = await list_indexes(client=client, workspace="test")

    assert isinstance(result, PaginatedResponse)
    assert len(result.data) == 0


@pytest.mark.asyncio
async def test_list_indexes_returns_indexes() -> None:
    index1 = create_test_index(name="index1", description="First index")
    index2 = create_test_index(name="index2", description="Second index")

    resource = FakeIndexResource(list_response=PaginatedResponse(data=[index1, index2], has_more=False, total=2))
    client = FakeClient(resource)

    result = await list_indexes(client=client, workspace="test")

    assert isinstance(result, PaginatedResponse)
    assert len(result.data) == 2
    assert result.data[0].name == index1.name
    assert result.data[1].name == index2.name


@pytest.mark.asyncio
async def test_list_indexes_with_cursor() -> None:
    index1 = create_test_index(name="index1", description="First index")
    index2 = create_test_index(name="index2", description="Second index")

    resource = FakeIndexResource(
        list_response=PaginatedResponse(data=[index1, index2], has_more=True, total=5, next_cursor="cursor123")
    )
    client = FakeClient(resource)

    result = await list_indexes(client=client, workspace="test", after="cursor456")

    assert isinstance(result, PaginatedResponse)
    assert len(result.data) == 2
    assert result.has_more is True
    assert result.next_cursor == "cursor123"


@pytest.mark.asyncio
async def test_list_indexes_returns_string_on_non_existant_workspace() -> None:
    resource = FakeIndexResource(list_exception=ResourceNotFoundError(message="Resource not found."))
    client = FakeClient(resource)

    result = await list_indexes(client=client, workspace="test")

    assert isinstance(result, str)
    assert result == "There is no workspace named 'test'. Did you mean to configure it?"


@pytest.mark.asyncio
async def test_get_index_returns_index() -> None:
    index = create_test_index(name="my_index", description="My special index")
    resource = FakeIndexResource(get_response=index)
    client = FakeClient(resource)

    result = await get_index(client=client, workspace="test", index_name="my_index")

    assert isinstance(result, Index)
    assert result.name == "my_index"


@pytest.mark.asyncio
async def test_get_index_returns_error_message_when_index_not_found() -> None:
    resource = FakeIndexResource(get_exception=ResourceNotFoundError())
    client = FakeClient(resource)

    result = await get_index(client=client, workspace="test", index_name="nonexistent")

    assert "There is no index named 'nonexistent'" in result


@pytest.mark.asyncio
async def test_create_index_returns_success_message_and_index() -> None:
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

    assert isinstance(result, dict)
    assert isinstance(result.get("message"), str)
    index = result.get("index")
    assert isinstance(index, Index)
    assert index.name == "new_index"


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
async def test_update_index_not_found_on_get() -> None:
    resource = FakeIndexResource(get_exception=ResourceNotFoundError())
    client = FakeClient(resource)
    result = await update_index(
        client=client, workspace="ws", index_name="np", original_config_snippet="x", replacement_config_snippet="y"
    )
    assert isinstance(result, str)
    assert "no index named 'np'" in result.lower()


@pytest.mark.asyncio
async def test_update_index_no_occurrences() -> None:
    original = create_test_index(
        name="np",
        yaml_config="foo: bar",
    )
    resource = FakeIndexResource(get_response=original)
    client = FakeClient(resource)
    result = await update_index(
        client=client,
        workspace="ws",
        index_name="np",
        original_config_snippet="baz",
        replacement_config_snippet="qux",
    )
    assert "No occurrences" in result


@pytest.mark.asyncio
async def test_update_index_multiple_occurrences() -> None:
    yaml = "dup: x\ndup: x"
    original = create_test_index(
        name="np",
        yaml_config=yaml,
    )
    resource = FakeIndexResource(get_response=original)
    client = FakeClient(resource)
    result = await update_index(
        client=client,
        workspace="ws",
        index_name="np",
        original_config_snippet="dup: x",
        replacement_config_snippet="z",
    )
    assert "Multiple occurrences (2)" in result


@pytest.mark.asyncio
async def test_update_index_no_yaml_config() -> None:
    original = create_test_index(
        name="np",
        yaml_config="",
    )
    # Manually set yaml_config to None to test this case
    original.yaml_config = None  # type: ignore[assignment]
    resource = FakeIndexResource(get_response=original)
    client = FakeClient(resource)
    result = await update_index(
        client=client,
        workspace="ws",
        index_name="np",
        original_config_snippet="foo: 1",
        replacement_config_snippet="foo: 2",
    )
    assert "does not have a YAML configuration" in result


@pytest.mark.asyncio
async def test_update_index_exceptions_on_update() -> None:
    orig_yaml = "foo: 1"
    original = create_test_index(
        name="np",
        yaml_config=orig_yaml,
    )
    val_ok = PipelineValidationResult(valid=True, errors=[])

    # ResourceNotFoundError
    res_not_found = FakeIndexResource(
        get_response=original, validate_response=val_ok, update_exception=ResourceNotFoundError()
    )
    client_not_found = FakeClient(res_not_found)
    r1 = await update_index(
        client=client_not_found,
        workspace="ws",
        index_name="np",
        original_config_snippet="foo: 1",
        replacement_config_snippet="foo: 2",
    )
    assert isinstance(r1, str)
    assert "no index named 'np'" in r1.lower()

    # BadRequestError
    res_bad = FakeIndexResource(
        get_response=original, validate_response=val_ok, update_exception=BadRequestError("bad request")
    )
    client_bad = FakeClient(res_bad)
    r2 = await update_index(
        client=client_bad,
        workspace="ws",
        index_name="np",
        original_config_snippet="foo: 1",
        replacement_config_snippet="foo: 2",
    )
    assert "Failed to update" in r2
    assert "bad request" in r2

    # UnexpectedAPIError
    res_unexp = FakeIndexResource(
        get_response=original,
        validate_response=val_ok,
        update_exception=UnexpectedAPIError(status_code=500, message="oops"),
    )
    client_unexp = FakeClient(res_unexp)
    r3 = await update_index(
        client=client_unexp,
        workspace="ws",
        index_name="np",
        original_config_snippet="foo: 1",
        replacement_config_snippet="foo: 2",
    )
    assert "Failed to update" in r3
    assert "oops" in r3


@pytest.mark.asyncio
async def test_update_index_success_response() -> None:
    orig_yaml = "foo: 1"
    original = create_test_index(
        name="np",
        yaml_config=orig_yaml,
    )
    updated = create_test_index(
        name="np",
        yaml_config="foo: 2",
    )
    val_ok = PipelineValidationResult(valid=True, errors=[])

    # success
    res_succ = FakeIndexResource(
        get_responses=[original, updated],  # First get returns original, second returns updated
        validate_response=val_ok,
        update_response=updated,
    )
    client_succ = FakeClient(res_succ)
    r_success = await update_index(
        client=client_succ,
        workspace="ws",
        index_name="np",
        original_config_snippet="foo: 1",
        replacement_config_snippet="foo: 2",
    )
    assert isinstance(r_success, Index)
    assert r_success.yaml_config == "foo: 2"


@pytest.mark.asyncio
async def test_update_index_validation_failure() -> None:
    orig_yaml = "foo: 1"
    original = create_test_index(
        name="np",
        yaml_config=orig_yaml,
    )
    invalid_val = PipelineValidationResult(valid=False, errors=[ValidationError(code="E", message="err")])
    resource = FakeIndexResource(get_response=original, validate_response=invalid_val)
    client = FakeClient(resource)
    result = await update_index(
        client=client,
        workspace="ws",
        index_name="np",
        original_config_snippet="foo: 1",
        replacement_config_snippet="foo: 2",
        skip_validation_errors=False,
    )
    assert isinstance(result, str)
    assert "Index validation failed" in result
    assert "E: err" in result


@pytest.mark.asyncio
async def test_update_index_skip_validation_errors_true() -> None:
    """Test that update_index updates the index despite validation errors."""
    from deepset_mcp.tools.indexes import IndexOperationWithErrors

    orig_yaml = "foo: 1"
    original = create_test_index(
        name="np",
        yaml_config=orig_yaml,
    )
    updated = create_test_index(
        name="np",
        yaml_config="foo: 2",
    )
    invalid_result = PipelineValidationResult(
        valid=False, errors=[ValidationError(code="E1", message="Test error message")]
    )

    resource = FakeIndexResource(
        get_responses=[original, updated],
        validate_response=invalid_result,
        update_response=updated,
    )
    client = FakeClient(resource)

    # Test with explicit True
    result = await update_index(
        client=client,
        workspace="ws",
        index_name="np",
        original_config_snippet="foo: 1",
        replacement_config_snippet="foo: 2",
        skip_validation_errors=True,
    )

    assert isinstance(result, IndexOperationWithErrors)
    assert result.message == "The operation completed with errors"
    assert result.validation_result == invalid_result
    assert result.index.yaml_config == "foo: 2"

    # Reset call count for second test
    resource._get_call_count = 0

    # Test with default (should behave the same as True)
    result_default = await update_index(
        client=client,
        workspace="ws",
        index_name="np",
        original_config_snippet="foo: 1",
        replacement_config_snippet="foo: 2",
    )

    assert isinstance(result_default, IndexOperationWithErrors)
    assert result_default.message == "The operation completed with errors"
    assert result_default.validation_result == invalid_result
    assert result_default.index.yaml_config == "foo: 2"


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
async def test_deploy_index_returns_success_message() -> None:
    """Test successful index deployment."""
    resource = FakeIndexResource(deploy_response=PipelineValidationResult(valid=True))
    client = FakeClient(resource)

    result = await deploy_index(client=client, workspace="test", index_name="test_index")

    assert "Index 'test_index' deployed successfully." == result


@pytest.mark.asyncio
async def test_deploy_index_returns_validation_errors() -> None:
    """Test deployment with validation errors."""
    validation_errors = [
        ValidationError(code="invalid_config", message="Index configuration is invalid"),
        ValidationError(code="missing_dependency", message="Required dependency not found"),
    ]
    validation_result = PipelineValidationResult(valid=False, errors=validation_errors)
    resource = FakeIndexResource(deploy_response=validation_result)
    client = FakeClient(resource)

    result = await deploy_index(client=client, workspace="test", index_name="test_index")

    assert isinstance(result, PipelineValidationResult)
    assert result.errors == validation_errors


@pytest.mark.parametrize(
    "error_class,expected_message",
    [
        (ResourceNotFoundError, "There is no index named 'test_index' in workspace 'test'"),
        (BadRequestError, "Failed to deploy index 'test_index'"),
        (UnexpectedAPIError, "Failed to deploy index 'test_index'"),
    ],
)
@pytest.mark.asyncio
async def test_deploy_index_returns_error_message(
    error_class: type[Exception],
    expected_message: str,
) -> None:
    """Test deployment error handling."""
    resource = FakeIndexResource(deploy_exception=error_class("Error details"))
    client = FakeClient(resource)

    result = await deploy_index(client=client, workspace="test", index_name="test_index")

    assert expected_message in result


@pytest.mark.asyncio
async def test_deploy_index_with_detailed_error_messages() -> None:
    """Test deployment with detailed error messages."""
    # Test BadRequestError with detailed message
    resource_bad = FakeIndexResource(deploy_exception=BadRequestError(message="Invalid index configuration"))
    client_bad = FakeClient(resource_bad)

    result_bad = await deploy_index(client=client_bad, workspace="test", index_name="bad_index")

    assert "Failed to deploy index 'bad_index'" in result_bad
    assert "Invalid index configuration" in result_bad
    assert "400" in result_bad

    # Test UnexpectedAPIError with status code
    resource_unexpected = FakeIndexResource(
        deploy_exception=UnexpectedAPIError(status_code=503, message="Service unavailable")
    )
    client_unexpected = FakeClient(resource_unexpected)

    result_unexpected = await deploy_index(client=client_unexpected, workspace="test", index_name="unavailable_index")

    assert "Failed to deploy index 'unavailable_index'" in result_unexpected
    assert "Service unavailable" in result_unexpected
    assert "503" in result_unexpected


# Validate index tests


@pytest.mark.asyncio
async def test_validate_index_empty_yaml_returns_message() -> None:
    client = FakeClient(FakeIndexResource())
    result = await validate_index(client=client, workspace="ws", yaml_configuration="   ")
    assert result == "You need to provide a YAML configuration to validate."


@pytest.mark.asyncio
async def test_validate_index_invalid_yaml_returns_error() -> None:
    client = FakeClient(FakeIndexResource())
    invalid_yaml = "invalid: : yaml"
    result = await validate_index(client=client, workspace="ws", yaml_configuration=invalid_yaml)
    assert isinstance(result, str)
    assert result.startswith("Invalid YAML provided:")


@pytest.mark.asyncio
async def test_validate_index_validates_via_client_and_returns_model() -> None:
    valid_result = PipelineValidationResult(valid=True, errors=[])
    invalid_result = PipelineValidationResult(
        valid=False,
        errors=[ValidationError(code="E1", message="Oops"), ValidationError(code="E2", message="Bad")],
    )

    # Test valid
    resource_valid = FakeIndexResource(validate_response=valid_result)
    client_valid = FakeClient(resource_valid)
    res_valid = await validate_index(client=client_valid, workspace="ws", yaml_configuration="a: b")
    assert isinstance(res_valid, IndexValidationResultWithYaml)
    assert res_valid.validation_result.valid is True
    assert res_valid.yaml_config == "a: b"

    # Test invalid
    resource_invalid = FakeIndexResource(validate_response=invalid_result)
    client_invalid = FakeClient(resource_invalid)
    res_invalid = await validate_index(client=client_invalid, workspace="ws", yaml_configuration="a: b")
    assert isinstance(res_invalid, IndexValidationResultWithYaml)
    assert res_invalid.validation_result.valid is False
    assert len(res_invalid.validation_result.errors) == 2
    assert res_invalid.validation_result.errors[0].code == "E1"


@pytest.mark.asyncio
async def test_validate_index_workspace_not_found() -> None:
    resource = FakeIndexResource(validate_exception=ResourceNotFoundError())
    client = FakeClient(resource)
    result = await validate_index(client=client, workspace="nonexistent", yaml_configuration="a: b")
    assert "There is no workspace named 'nonexistent'. Did you mean to configure it?" == result


@pytest.mark.asyncio
async def test_validate_index_bad_request_error() -> None:
    resource = FakeIndexResource(validate_exception=BadRequestError("Invalid configuration"))
    client = FakeClient(resource)
    result = await validate_index(client=client, workspace="ws", yaml_configuration="a: b")
    assert "Failed to validate index: Invalid configuration (Status Code: 400)" == result


@pytest.mark.asyncio
async def test_validate_index_unexpected_api_error() -> None:
    resource = FakeIndexResource(validate_exception=UnexpectedAPIError(status_code=500, message="Server error"))
    client = FakeClient(resource)
    result = await validate_index(client=client, workspace="ws", yaml_configuration="a: b")
    assert "Failed to validate index: Server error (Status Code: 500)" == result
