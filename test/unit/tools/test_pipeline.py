# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

import pytest

from deepset_mcp.api.exceptions import (
    BadRequestError,
    ResourceNotFoundError,
    UnexpectedAPIError,
)
from deepset_mcp.api.pipeline.log_level import LogLevel
from deepset_mcp.api.pipeline.models import (
    DeepsetAnswer,
    DeepsetDocument,
    DeepsetPipeline,
    DeepsetSearchResponse,
    DeepsetStreamEvent,
    ExceptionInfo,
    PipelineList,
    PipelineLog,
    PipelineLogList,
    PipelineOperationWithErrors,
    PipelineServiceLevel,
    PipelineValidationResult,
    PipelineValidationResultWithYaml,
    ValidationError,
)
from deepset_mcp.api.shared_models import DeepsetUser, NoContentResponse

# Adjust the import path below to match your project structure
from deepset_mcp.tools.pipeline import (
    create_pipeline,
    deploy_pipeline,
    get_pipeline,
    get_pipeline_logs,
    list_pipelines,
    search_pipeline,
    update_pipeline,
    validate_pipeline,
)
from test.unit.conftest import BaseFakeClient


class FakePipelineResource:
    def __init__(
        self,
        list_response: list[DeepsetPipeline] | None = None,
        get_response: DeepsetPipeline | None = None,
        get_responses: list[DeepsetPipeline] | None = None,  # For sequential responses during waiting
        validate_response: PipelineValidationResult | None = None,
        create_response: NoContentResponse | None = None,
        update_response: NoContentResponse | None = None,
        logs_response: PipelineLogList | None = None,
        deploy_response: PipelineValidationResult | None = None,
        search_response: DeepsetSearchResponse | None = None,
        get_exception: Exception | None = None,
        update_exception: Exception | None = None,
        create_exception: Exception | None = None,
        logs_exception: Exception | None = None,
        deploy_exception: Exception | None = None,
        search_exception: Exception | None = None,
        list_exception: Exception | None = None,
    ) -> None:
        self._list_response = list_response
        self._get_response = get_response
        self._get_responses = get_responses or []
        self._get_call_count = 0
        self._validate_response = validate_response
        self._create_response = create_response
        self._create_exception = create_exception
        self._update_response = update_response
        self._get_exception = get_exception
        self._update_exception = update_exception
        self._logs_response = logs_response
        self._logs_exception = logs_exception
        self._deploy_response = deploy_response
        self._deploy_exception = deploy_exception
        self._search_response = search_response
        self._search_exception = search_exception
        self._list_exception = list_exception

    async def list(self, page_number: int = 1, limit: int = 10) -> PipelineList:
        if self._list_exception:
            raise self._list_exception
        if self._list_response is not None:
            return PipelineList(data=self._list_response, has_more=False, total=len(self._list_response))
        raise NotImplementedError

    async def get(self, pipeline_name: str, include_yaml: bool = True) -> DeepsetPipeline:
        if self._get_exception:
            raise self._get_exception

        # If we have multiple responses for sequential calls (used for waiting tests)
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

    async def validate(self, yaml_config: str) -> PipelineValidationResult:
        if self._validate_response is not None:
            return self._validate_response
        raise NotImplementedError

    async def create(self, name: str, yaml_config: str) -> NoContentResponse:
        if self._create_exception:
            raise self._create_exception
        if self._create_response is not None:
            return self._create_response
        raise NotImplementedError

    async def update(
        self,
        pipeline_name: str,
        updated_pipeline_name: str | None = None,
        yaml_config: str | None = None,
    ) -> NoContentResponse:
        if self._update_exception:
            raise self._update_exception
        if self._update_response is not None:
            return self._update_response
        raise NotImplementedError

    async def get_logs(
        self,
        pipeline_name: str,
        limit: int = 30,
        level: LogLevel | None = None,
    ) -> PipelineLogList:
        if self._logs_exception:
            raise self._logs_exception
        if self._logs_response is not None:
            return self._logs_response
        raise NotImplementedError

    async def deploy(self, pipeline_name: str) -> PipelineValidationResult:
        if self._deploy_exception:
            raise self._deploy_exception
        if self._deploy_response is not None:
            return self._deploy_response
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
        """Search using a pipeline."""
        if self._search_exception:
            raise self._search_exception
        if self._search_response is not None:
            return self._search_response
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
        """Search using a pipeline with response streaming."""
        raise NotImplementedError

    async def delete(self, pipeline_name: str) -> NoContentResponse:
        """Delete a pipeline."""
        raise NotImplementedError


class FakeClient(BaseFakeClient):
    def __init__(self, resource: FakePipelineResource) -> None:
        self._resource = resource
        super().__init__()

    def pipelines(self, workspace: str) -> FakePipelineResource:
        return self._resource


@pytest.mark.asyncio
async def test_list_pipelines_returns_pipeline_list() -> None:
    user = DeepsetUser(user_id="u1", given_name="Alice", family_name="Smith")
    pipeline1 = DeepsetPipeline(
        pipeline_id="p1",
        name="pipeline1",
        status="ACTIVE",
        service_level=PipelineServiceLevel.DEVELOPMENT,
        created_at=datetime(2021, 1, 1, 12, 0),
        last_edited_at=None,
        created_by=user,
        last_edited_by=None,
        yaml_config=None,
    )
    pipeline2 = DeepsetPipeline(
        pipeline_id="p2",
        name="pipeline2",
        status="INACTIVE",
        service_level=PipelineServiceLevel.DRAFT,
        created_at=datetime(2022, 2, 2, 14, 30),
        last_edited_at=datetime(2022, 3, 3, 15, 45),
        created_by=user,
        last_edited_by=user,
        yaml_config="config: value",
    )
    resource = FakePipelineResource(list_response=[pipeline1, pipeline2])
    client = FakeClient(resource)
    result = await list_pipelines(client=client, workspace="ws1")
    assert isinstance(result, PipelineList)
    assert len(result.data) == 2
    assert result.data[0].name == "pipeline1"
    assert result.data[1].name == "pipeline2"


@pytest.mark.asyncio
async def test_get_pipeline_returns_pipeline_object() -> None:
    user = DeepsetUser(user_id="u1", given_name="Bob", family_name="Jones")
    pipeline = DeepsetPipeline(
        pipeline_id="pX",
        name="mypipe",
        status="RUNNING",
        service_level=PipelineServiceLevel.PRODUCTION,
        created_at=datetime(2023, 5, 5, 10, 0),
        last_edited_at=None,
        created_by=user,
        last_edited_by=None,
        yaml_config="foo: bar",
    )
    resource = FakePipelineResource(get_response=pipeline)
    client = FakeClient(resource)
    result = await get_pipeline(client=client, workspace="ws2", pipeline_name="mypipe")
    assert isinstance(result, DeepsetPipeline)
    assert result.name == "mypipe"
    assert result.yaml_config == "foo: bar"


@pytest.mark.asyncio
async def test_validate_pipeline_empty_yaml_returns_message() -> None:
    client = FakeClient(FakePipelineResource())
    result = await validate_pipeline(client=client, workspace="ws", yaml_configuration="   ")
    assert result == "You need to provide a YAML configuration to validate."


@pytest.mark.asyncio
async def test_validate_pipeline_invalid_yaml_returns_error() -> None:
    client = FakeClient(FakePipelineResource())
    invalid_yaml = "invalid: : yaml"
    result = await validate_pipeline(client=client, workspace="ws", yaml_configuration=invalid_yaml)
    assert isinstance(result, str)
    assert result.startswith("Invalid YAML provided:")


@pytest.mark.asyncio
async def test_validate_pipeline_validates_via_client_and_returns_model() -> None:
    valid_result = PipelineValidationResult(valid=True, errors=[])
    invalid_result = PipelineValidationResult(
        valid=False,
        errors=[ValidationError(code="E1", message="Oops"), ValidationError(code="E2", message="Bad")],
    )
    # Test valid
    resource_valid = FakePipelineResource(validate_response=valid_result)
    client_valid = FakeClient(resource_valid)
    res_valid = await validate_pipeline(client=client_valid, workspace="ws", yaml_configuration="a: b")
    assert isinstance(res_valid, PipelineValidationResultWithYaml)
    assert res_valid.validation_result.valid is True
    assert res_valid.yaml_config == "a: b"
    # Test invalid
    resource_invalid = FakePipelineResource(validate_response=invalid_result)
    client_invalid = FakeClient(resource_invalid)
    res_invalid = await validate_pipeline(client=client_invalid, workspace="ws", yaml_configuration="a: b")
    assert isinstance(res_invalid, PipelineValidationResultWithYaml)
    assert res_invalid.validation_result.valid is False
    assert len(res_invalid.validation_result.errors) == 2
    assert res_invalid.validation_result.errors[0].code == "E1"


@pytest.mark.asyncio
async def test_create_pipeline_handles_validation_failure() -> None:
    invalid_result = PipelineValidationResult(valid=False, errors=[ValidationError(code="E", message="Err")])
    resource = FakePipelineResource(validate_response=invalid_result)
    client = FakeClient(resource)
    result = await create_pipeline(
        client=client, workspace="ws", pipeline_name="pname", yaml_configuration="cfg", skip_validation_errors=False
    )
    assert isinstance(result, str)
    assert "Pipeline validation failed" in result
    assert "E: Err" in result


@pytest.mark.asyncio
async def test_create_pipeline_handles_success_and_failure_response() -> None:
    user = DeepsetUser(user_id="u1", given_name="Alice", family_name="Smith")
    valid_result = PipelineValidationResult(valid=True, errors=[])
    created_pipeline = DeepsetPipeline(
        pipeline_id="p1",
        name="p1",
        status="DRAFT",
        service_level=PipelineServiceLevel.DEVELOPMENT,
        created_at=datetime(2023, 1, 1, 12, 0),
        last_edited_at=None,
        created_by=user,
        last_edited_by=None,
        yaml_config="a: b",
    )

    # success
    resource_succ = FakePipelineResource(
        validate_response=valid_result,
        create_response=NoContentResponse(message="created successfully"),
        get_response=created_pipeline,
    )
    client_succ = FakeClient(resource_succ)
    res_succ = await create_pipeline(client=client_succ, workspace="ws", pipeline_name="p1", yaml_configuration="a: b")

    assert isinstance(res_succ, DeepsetPipeline)
    assert res_succ.name == "p1"

    # failure
    resource_fail = FakePipelineResource(
        validate_response=valid_result,
        create_exception=BadRequestError(message="bad things"),
    )
    client_fail = FakeClient(resource_fail)
    res_fail = await create_pipeline(client=client_fail, workspace="ws", pipeline_name="p1", yaml_configuration="a: b")
    assert isinstance(res_fail, str)
    assert "Failed to create pipeline 'p1': bad things (Status Code: 400)" == res_fail


@pytest.mark.asyncio
async def test_create_pipeline_skip_validation_errors_true() -> None:
    """Test that create_pipeline creates the pipeline despite validation errors."""
    user = DeepsetUser(user_id="u1", given_name="Alice", family_name="Smith")
    invalid_result = PipelineValidationResult(
        valid=False, errors=[ValidationError(code="E1", message="Test error message")]
    )
    created_pipeline = DeepsetPipeline(
        pipeline_id="p1",
        name="test_pipeline",
        status="DRAFT",
        service_level=PipelineServiceLevel.DEVELOPMENT,
        created_at=datetime(2023, 1, 1, 12, 0),
        last_edited_at=None,
        created_by=user,
        last_edited_by=None,
        yaml_config="config: test",
    )
    resource = FakePipelineResource(
        validate_response=invalid_result,
        create_response=NoContentResponse(message="created successfully"),
        get_response=created_pipeline,
    )
    client = FakeClient(resource)

    # Test with explicit True
    result = await create_pipeline(
        client=client,
        workspace="ws",
        pipeline_name="test_pipeline",
        yaml_configuration="config: test",
        skip_validation_errors=True,
    )

    assert isinstance(result, PipelineOperationWithErrors)
    assert result.message == "The operation completed with errors"
    assert result.validation_result.valid is False
    assert len(result.validation_result.errors) == 1
    assert result.validation_result.errors[0].code == "E1"
    assert result.pipeline.name == "test_pipeline"

    # Reset call count for the second test
    resource._get_call_count = 0

    # Test with default (should behave the same as True)
    result_default = await create_pipeline(
        client=client, workspace="ws", pipeline_name="test_pipeline", yaml_configuration="config: test"
    )

    assert isinstance(result_default, PipelineOperationWithErrors)
    assert result_default.message == "The operation completed with errors"
    assert result_default.pipeline.name == "test_pipeline"


@pytest.mark.asyncio
async def test_update_pipeline_not_found_on_get() -> None:
    resource = FakePipelineResource(get_exception=ResourceNotFoundError())
    client = FakeClient(resource)
    res = await update_pipeline(
        client=client, workspace="ws", pipeline_name="np", original_config_snippet="x", replacement_config_snippet="y"
    )
    assert isinstance(res, str)
    assert "no pipeline named 'np'" in res.lower()


@pytest.mark.asyncio
async def test_update_pipeline_no_occurrences() -> None:
    user = DeepsetUser(user_id="u1", given_name="A", family_name="B")
    original = DeepsetPipeline(
        pipeline_id="p",
        name="np",
        status="S",
        service_level=PipelineServiceLevel.DRAFT,
        created_at=datetime.now(),
        last_edited_at=None,
        created_by=user,
        last_edited_by=None,
        yaml_config="foo: bar",
    )
    resource = FakePipelineResource(get_response=original)
    client = FakeClient(resource)
    res = await update_pipeline(
        client=client,
        workspace="ws",
        pipeline_name="np",
        original_config_snippet="baz",
        replacement_config_snippet="qux",
    )
    assert "No occurrences" in res


@pytest.mark.asyncio
async def test_update_pipeline_multiple_occurrences() -> None:
    user = DeepsetUser(user_id="u1", given_name="A", family_name="B")
    yaml = "dup: x\ndup: x"
    original = DeepsetPipeline(
        pipeline_id="p",
        name="np",
        status="S",
        service_level=PipelineServiceLevel.DRAFT,
        created_at=datetime.now(),
        last_edited_at=None,
        created_by=user,
        last_edited_by=None,
        yaml_config=yaml,
    )
    resource = FakePipelineResource(get_response=original)
    client = FakeClient(resource)
    res = await update_pipeline(
        client=client,
        workspace="ws",
        pipeline_name="np",
        original_config_snippet="dup: x",
        replacement_config_snippet="z",
    )
    assert "Multiple occurrences (2)" in res


@pytest.mark.asyncio
async def test_update_pipeline_validation_failure() -> None:
    user = DeepsetUser(user_id="u1", given_name="A", family_name="B")
    orig_yaml = "foo: 1"
    original = DeepsetPipeline(
        pipeline_id="p",
        name="np",
        status="S",
        service_level=PipelineServiceLevel.DRAFT,
        created_at=datetime.now(),
        last_edited_at=None,
        created_by=user,
        last_edited_by=None,
        yaml_config=orig_yaml,
    )
    invalid_val = PipelineValidationResult(valid=False, errors=[ValidationError(code="E", message="err")])
    resource = FakePipelineResource(get_response=original, validate_response=invalid_val)
    client = FakeClient(resource)
    res = await update_pipeline(
        client=client,
        workspace="ws",
        pipeline_name="np",
        original_config_snippet="foo: 1",
        replacement_config_snippet="foo: 2",
        skip_validation_errors=False,
    )
    assert isinstance(res, str)
    assert "Pipeline validation failed" in res
    assert "E: err" in res


@pytest.mark.asyncio
async def test_update_pipeline_exceptions_on_update() -> None:
    user = DeepsetUser(user_id="u1", given_name="A", family_name="B")
    orig_yaml = "foo: 1"
    original = DeepsetPipeline(
        pipeline_id="p",
        name="np",
        status="S",
        service_level=PipelineServiceLevel.DRAFT,
        created_at=datetime.now(),
        last_edited_at=None,
        created_by=user,
        last_edited_by=None,
        yaml_config=orig_yaml,
    )
    val_ok = PipelineValidationResult(valid=True, errors=[])
    # ResourceNotFoundError
    res_not_found = FakePipelineResource(
        get_response=original, validate_response=val_ok, update_exception=ResourceNotFoundError()
    )
    client_not_found = FakeClient(res_not_found)
    r1 = await update_pipeline(
        client=client_not_found,
        workspace="ws",
        pipeline_name="np",
        original_config_snippet="foo: 1",
        replacement_config_snippet="foo: 2",
    )
    assert isinstance(r1, str)
    assert "no pipeline named 'np'" in r1.lower()
    # BadRequestError
    res_bad = FakePipelineResource(
        get_response=original, validate_response=val_ok, update_exception=BadRequestError("bad request")
    )
    client_bad = FakeClient(res_bad)
    r2 = await update_pipeline(
        client=client_bad,
        workspace="ws",
        pipeline_name="np",
        original_config_snippet="foo: 1",
        replacement_config_snippet="foo: 2",
    )
    assert "Failed to update" in r2
    assert "bad request" in r2
    # UnexpectedAPIError
    res_unexp = FakePipelineResource(
        get_response=original,
        validate_response=val_ok,
        update_exception=UnexpectedAPIError(status_code=500, message="oops"),
    )
    client_unexp = FakeClient(res_unexp)
    r3 = await update_pipeline(
        client=client_unexp,
        workspace="ws",
        pipeline_name="np",
        original_config_snippet="foo: 1",
        replacement_config_snippet="foo: 2",
    )
    assert "Failed to update" in r3
    assert "oops" in r3


@pytest.mark.asyncio
async def test_update_pipeline_success_response() -> None:
    user = DeepsetUser(user_id="u1", given_name="A", family_name="B")
    orig_yaml = "foo: 1"
    original = DeepsetPipeline(
        pipeline_id="p",
        name="np",
        status="S",
        service_level=PipelineServiceLevel.DEVELOPMENT,
        created_at=datetime.now(),
        last_edited_at=None,
        created_by=user,
        last_edited_by=None,
        yaml_config=orig_yaml,
    )
    updated = DeepsetPipeline(
        pipeline_id="p",
        name="np",
        status="S",
        service_level=PipelineServiceLevel.DEVELOPMENT,
        created_at=datetime.now(),
        last_edited_at=None,
        created_by=user,
        last_edited_by=None,
        yaml_config="foo: 2",
    )
    val_ok = PipelineValidationResult(valid=True, errors=[])

    # success
    res_succ = FakePipelineResource(
        get_responses=[original, updated],  # First get returns original, second returns updated
        validate_response=val_ok,
        update_response=NoContentResponse(message="successfully updated"),
    )
    client_succ = FakeClient(res_succ)
    r_success = await update_pipeline(
        client=client_succ,
        workspace="ws",
        pipeline_name="np",
        original_config_snippet="foo: 1",
        replacement_config_snippet="foo: 2",
    )
    assert isinstance(r_success, DeepsetPipeline)
    assert r_success.yaml_config == "foo: 2"


@pytest.mark.asyncio
async def test_update_pipeline_skip_validation_errors_true() -> None:
    """Test that update_pipeline updates the pipeline despite validation errors."""
    user = DeepsetUser(user_id="u1", given_name="A", family_name="B")
    orig_yaml = "foo: 1"
    original = DeepsetPipeline(
        pipeline_id="p",
        name="np",
        status="S",
        service_level=PipelineServiceLevel.DEVELOPMENT,
        created_at=datetime.now(),
        last_edited_at=None,
        created_by=user,
        last_edited_by=None,
        yaml_config=orig_yaml,
    )
    updated = DeepsetPipeline(
        pipeline_id="p",
        name="np",
        status="S",
        service_level=PipelineServiceLevel.DEVELOPMENT,
        created_at=datetime.now(),
        last_edited_at=None,
        created_by=user,
        last_edited_by=None,
        yaml_config="foo: 2",
    )
    invalid_result = PipelineValidationResult(
        valid=False, errors=[ValidationError(code="E1", message="Test error message")]
    )

    resource = FakePipelineResource(
        get_responses=[original, updated],
        validate_response=invalid_result,
        update_response=NoContentResponse(message="successfully updated"),
    )
    client = FakeClient(resource)

    # Test with explicit True
    result = await update_pipeline(
        client=client,
        workspace="ws",
        pipeline_name="np",
        original_config_snippet="foo: 1",
        replacement_config_snippet="foo: 2",
        skip_validation_errors=True,
    )

    assert isinstance(result, PipelineOperationWithErrors)
    assert result.message == "The operation completed with errors"
    assert result.validation_result == invalid_result
    assert result.pipeline.yaml_config == "foo: 2"

    # Reset call count for second test
    resource._get_call_count = 0

    # Test with default (should behave the same as True)
    result_default = await update_pipeline(
        client=client,
        workspace="ws",
        pipeline_name="np",
        original_config_snippet="foo: 1",
        replacement_config_snippet="foo: 2",
    )

    assert isinstance(result_default, PipelineOperationWithErrors)
    assert result_default.message == "The operation completed with errors"
    assert result_default.validation_result == invalid_result
    assert result_default.pipeline.yaml_config == "foo: 2"


@pytest.mark.asyncio
async def test_get_pipeline_logs_success() -> None:
    log1 = PipelineLog(
        log_id="log1",
        message="Pipeline started",
        logged_at=datetime(2023, 1, 1, 12, 0, 0),
        level="info",
        origin="querypipeline",
        exceptions=None,
        extra_fields={},
    )
    log2 = PipelineLog(
        log_id="log2",
        message="Error occurred",
        logged_at=datetime(2023, 1, 1, 12, 1, 0),
        level="error",
        origin="querypipeline",
        exceptions=[ExceptionInfo(type="bla", value="bla", trace=[])],
        extra_fields={"component": "reader"},
    )
    logs = PipelineLogList(data=[log1, log2], has_more=False, total=2)

    resource = FakePipelineResource(logs_response=logs)
    client = FakeClient(resource)

    result = await get_pipeline_logs(client=client, workspace="ws", pipeline_name="test-pipeline")

    assert isinstance(result, PipelineLogList)
    assert len(result.data) == 2
    assert result.data[0].message == "Pipeline started"
    assert result.data[1].message == "Error occurred"
    assert result.data[0].level == "info"
    assert result.data[1].level == "error"


@pytest.mark.asyncio
async def test_get_pipeline_logs_empty() -> None:
    logs = PipelineLogList(data=[], has_more=False, total=0)

    resource = FakePipelineResource(logs_response=logs)
    client = FakeClient(resource)

    result = await get_pipeline_logs(client=client, workspace="ws", pipeline_name="test-pipeline")

    assert isinstance(result, PipelineLogList)
    assert len(result.data) == 0
    assert result.total == 0


@pytest.mark.asyncio
async def test_get_pipeline_logs_with_level_filter() -> None:
    logs = PipelineLogList(data=[], has_more=False, total=0)

    resource = FakePipelineResource(logs_response=logs)
    client = FakeClient(resource)

    result = await get_pipeline_logs(client=client, workspace="ws", pipeline_name="test-pipeline", level=LogLevel.ERROR)

    assert isinstance(result, PipelineLogList)
    assert len(result.data) == 0


@pytest.mark.asyncio
async def test_get_pipeline_logs_resource_not_found() -> None:
    resource = FakePipelineResource(logs_exception=ResourceNotFoundError())
    client = FakeClient(resource)

    result = await get_pipeline_logs(client=client, workspace="ws", pipeline_name="missing-pipeline")

    assert "There is no pipeline named 'missing-pipeline' in workspace 'ws'" in result


@pytest.mark.asyncio
async def test_get_pipeline_logs_bad_request() -> None:
    resource = FakePipelineResource(logs_exception=BadRequestError("Invalid level filter"))
    client = FakeClient(resource)

    result = await get_pipeline_logs(client=client, workspace="ws", pipeline_name="test-pipeline")

    assert "Failed to fetch logs for pipeline 'test-pipeline': Invalid level filter" in result


@pytest.mark.asyncio
async def test_get_pipeline_logs_unexpected_error() -> None:
    resource = FakePipelineResource(logs_exception=UnexpectedAPIError(status_code=500, message="Internal server error"))
    client = FakeClient(resource)

    result = await get_pipeline_logs(client=client, workspace="ws", pipeline_name="test-pipeline")

    assert "Failed to fetch logs for pipeline 'test-pipeline': Internal server error" in result


@pytest.mark.asyncio
async def test_deploy_pipeline_success() -> None:
    """Test successful pipeline deployment."""
    success_result = PipelineValidationResult(valid=True, errors=[])
    resource = FakePipelineResource(deploy_response=success_result)
    client = FakeClient(resource)

    result = await deploy_pipeline(client=client, workspace="ws", pipeline_name="test-pipeline")

    assert isinstance(result, PipelineValidationResult)
    assert result.valid is True
    assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_deploy_pipeline_with_validation_errors() -> None:
    """Test deployment with validation errors."""
    error_result = PipelineValidationResult(
        valid=False,
        errors=[
            ValidationError(code="INVALID_COMPONENT", message="Component 'invalid_reader' is not available"),
            ValidationError(code="MISSING_FIELD", message="Required field 'index' is missing"),
        ],
    )
    resource = FakePipelineResource(deploy_response=error_result)
    client = FakeClient(resource)

    result = await deploy_pipeline(client=client, workspace="ws", pipeline_name="test-pipeline")

    assert isinstance(result, PipelineValidationResult)
    assert result.valid is False
    assert len(result.errors) == 2
    assert result.errors[0].code == "INVALID_COMPONENT"
    assert result.errors[1].code == "MISSING_FIELD"


@pytest.mark.asyncio
async def test_deploy_pipeline_not_found() -> None:
    """Test deployment of non-existent pipeline."""
    resource = FakePipelineResource(deploy_exception=ResourceNotFoundError())
    client = FakeClient(resource)

    result = await deploy_pipeline(client=client, workspace="ws", pipeline_name="missing-pipeline")

    assert "There is no pipeline named 'missing-pipeline' in workspace 'ws'." == result


@pytest.mark.asyncio
async def test_deploy_pipeline_bad_request() -> None:
    """Test deployment with bad request error."""
    resource = FakePipelineResource(deploy_exception=BadRequestError("Pipeline is not ready for deployment"))
    client = FakeClient(resource)

    result = await deploy_pipeline(client=client, workspace="ws", pipeline_name="test-pipeline")

    assert "Failed to deploy pipeline 'test-pipeline': Pipeline is not ready for deployment" in result


@pytest.mark.asyncio
async def test_deploy_pipeline_unexpected_error() -> None:
    """Test deployment with unexpected API error."""
    resource = FakePipelineResource(
        deploy_exception=UnexpectedAPIError(status_code=500, message="Internal server error")
    )
    client = FakeClient(resource)

    result = await deploy_pipeline(client=client, workspace="ws", pipeline_name="test-pipeline")

    assert "Failed to deploy pipeline 'test-pipeline': Internal server error" in result


@pytest.mark.asyncio
async def test_deploy_pipeline_wait_for_deployment_success() -> None:
    """Test deployment with wait_for_deployment=True that succeeds."""
    user = DeepsetUser(user_id="u1", given_name="Alice", family_name="Smith")

    # Create pipeline responses showing progression from DEPLOYING to DEPLOYED
    pipeline_deploying = DeepsetPipeline(
        pipeline_id="p1",
        name="test-pipeline",
        status="DEPLOYING",
        service_level=PipelineServiceLevel.PRODUCTION,
        created_at=datetime(2023, 1, 1, 12, 0),
        last_edited_at=None,
        created_by=user,
        last_edited_by=None,
        yaml_config="config: test",
    )

    pipeline_deployed = DeepsetPipeline(
        pipeline_id="p1",
        name="test-pipeline",
        status="DEPLOYED",
        service_level=PipelineServiceLevel.PRODUCTION,
        created_at=datetime(2023, 1, 1, 12, 0),
        last_edited_at=None,
        created_by=user,
        last_edited_by=None,
        yaml_config="config: test",
    )

    success_result = PipelineValidationResult(valid=True, errors=[])
    resource = FakePipelineResource(
        deploy_response=success_result,
        get_responses=[pipeline_deploying, pipeline_deployed],  # First call returns DEPLOYING, second returns DEPLOYED
    )
    client = FakeClient(resource)

    result = await deploy_pipeline(
        client=client,
        workspace="ws",
        pipeline_name="test-pipeline",
        wait_for_deployment=True,
        timeout_seconds=60,  # Short timeout for test
        poll_interval=0.1,  # Short interval for test
    )

    assert isinstance(result, PipelineValidationResult)
    assert result.valid is True


@pytest.mark.asyncio
async def test_deploy_pipeline_wait_for_deployment_failed() -> None:
    """Test deployment with wait_for_deployment=True where deployment fails."""
    user = DeepsetUser(user_id="u1", given_name="Alice", family_name="Smith")

    # Create pipeline responses showing progression from DEPLOYING to FAILED
    pipeline_deploying = DeepsetPipeline(
        pipeline_id="p1",
        name="test-pipeline",
        status="DEPLOYING",
        service_level=PipelineServiceLevel.PRODUCTION,
        created_at=datetime(2023, 1, 1, 12, 0),
        last_edited_at=None,
        created_by=user,
        last_edited_by=None,
        yaml_config="config: test",
    )

    pipeline_failed = DeepsetPipeline(
        pipeline_id="p1",
        name="test-pipeline",
        status="FAILED",
        service_level=PipelineServiceLevel.PRODUCTION,
        created_at=datetime(2023, 1, 1, 12, 0),
        last_edited_at=None,
        created_by=user,
        last_edited_by=None,
        yaml_config="config: test",
    )

    success_result = PipelineValidationResult(valid=True, errors=[])
    resource = FakePipelineResource(
        deploy_response=success_result,
        get_responses=[pipeline_deploying, pipeline_failed],  # First call returns DEPLOYING, second returns FAILED
    )
    client = FakeClient(resource)

    result = await deploy_pipeline(
        client=client,
        workspace="ws",
        pipeline_name="test-pipeline",
        wait_for_deployment=True,
        timeout_seconds=60,
        poll_interval=0.1,
    )

    assert "Pipeline 'test-pipeline' deployment failed. Current status: FAILED." == result


@pytest.mark.asyncio
async def test_deploy_pipeline_wait_for_deployment_timeout() -> None:
    """Test deployment with wait_for_deployment=True that times out."""
    user = DeepsetUser(user_id="u1", given_name="Alice", family_name="Smith")

    # Create pipeline that stays in DEPLOYING state
    pipeline_deploying = DeepsetPipeline(
        pipeline_id="p1",
        name="test-pipeline",
        status="DEPLOYING",
        service_level=PipelineServiceLevel.PRODUCTION,
        created_at=datetime(2023, 1, 1, 12, 0),
        last_edited_at=None,
        created_by=user,
        last_edited_by=None,
        yaml_config="config: test",
    )

    success_result = PipelineValidationResult(valid=True, errors=[])
    resource = FakePipelineResource(
        deploy_response=success_result,
        get_response=pipeline_deploying,  # Always returns DEPLOYING
    )
    client = FakeClient(resource)

    result = await deploy_pipeline(
        client=client,
        workspace="ws",
        pipeline_name="test-pipeline",
        wait_for_deployment=True,
        timeout_seconds=0.2,  # Very short timeout for test
        poll_interval=0.1,
    )

    assert (
        "Pipeline 'test-pipeline' deployment initiated successfully, but did not reach DEPLOYED status "
        "within 0.2 seconds" in result
    )
    assert "You can check the pipeline status manually." in result


@pytest.mark.asyncio
async def test_deploy_pipeline_wait_for_deployment_get_error() -> None:
    """Test deployment with wait_for_deployment=True where get() fails during polling."""
    success_result = PipelineValidationResult(valid=True, errors=[])
    resource = FakePipelineResource(
        deploy_response=success_result,
        get_exception=BadRequestError("Pipeline status unavailable"),
    )
    client = FakeClient(resource)

    result = await deploy_pipeline(
        client=client,
        workspace="ws",
        pipeline_name="test-pipeline",
        wait_for_deployment=True,
        timeout_seconds=60,
        poll_interval=0.1,
    )

    assert "Pipeline 'test-pipeline' deployment initiated, but failed to check deployment status" in result
    assert "Pipeline status unavailable" in result


@pytest.mark.asyncio
async def test_deploy_pipeline_no_wait_backwards_compatibility() -> None:
    """Test that the function maintains backwards compatibility when wait_for_deployment is not specified."""
    success_result = PipelineValidationResult(valid=True, errors=[])
    resource = FakePipelineResource(deploy_response=success_result)
    client = FakeClient(resource)

    # Test with default parameters (should not wait)
    result = await deploy_pipeline(client=client, workspace="ws", pipeline_name="test-pipeline")

    assert isinstance(result, PipelineValidationResult)
    assert result.valid is True


@pytest.mark.asyncio
async def test_deploy_pipeline_wait_false_explicit() -> None:
    """Test deployment with explicit wait_for_deployment=False."""
    success_result = PipelineValidationResult(valid=True, errors=[])
    resource = FakePipelineResource(deploy_response=success_result)
    client = FakeClient(resource)

    result = await deploy_pipeline(
        client=client, workspace="ws", pipeline_name="test-pipeline", wait_for_deployment=False
    )

    assert isinstance(result, PipelineValidationResult)
    assert result.valid is True


# Search pipeline tests


@pytest.mark.asyncio
async def test_search_pipeline_success() -> None:
    """Test successful pipeline search."""
    user = DeepsetUser(user_id="u1", given_name="Alice", family_name="Smith")
    pipeline = DeepsetPipeline(
        pipeline_id="p1",
        name="test-pipeline",
        status="DEPLOYED",
        service_level=PipelineServiceLevel.PRODUCTION,
        created_at=datetime(2023, 1, 1, 12, 0),
        last_edited_at=None,
        created_by=user,
        last_edited_by=None,
        yaml_config="config: test",
    )

    answer = DeepsetAnswer(
        answer="The answer to your question is 42.",
        score=0.95,
        context="Some context about the answer",
    )

    search_response = DeepsetSearchResponse(
        query="What is the answer?",
        answers=[answer],
        documents=[],
    )

    resource = FakePipelineResource(
        get_response=pipeline,
        search_response=search_response,
    )
    client = FakeClient(resource)

    result = await search_pipeline(
        client=client, workspace="ws", pipeline_name="test-pipeline", query="What is the answer?"
    )

    assert isinstance(result, DeepsetSearchResponse)
    assert result.query == "What is the answer?"
    assert len(result.answers) == 1
    assert result.answers[0].answer == "The answer to your question is 42."


@pytest.mark.asyncio
async def test_search_pipeline_not_deployed() -> None:
    """Test search with pipeline that is not deployed."""
    user = DeepsetUser(user_id="u1", given_name="Alice", family_name="Smith")
    pipeline = DeepsetPipeline(
        pipeline_id="p1",
        name="test-pipeline",
        status="DRAFT",  # Not deployed
        service_level=PipelineServiceLevel.DEVELOPMENT,
        created_at=datetime(2023, 1, 1, 12, 0),
        last_edited_at=None,
        created_by=user,
        last_edited_by=None,
        yaml_config="config: test",
    )

    resource = FakePipelineResource(get_response=pipeline)
    client = FakeClient(resource)

    result = await search_pipeline(client=client, workspace="ws", pipeline_name="test-pipeline", query="test query")

    assert "Pipeline 'test-pipeline' is not deployed (current status: DRAFT)" in result
    assert "Please deploy the pipeline first" in result


@pytest.mark.asyncio
async def test_search_pipeline_not_found() -> None:
    """Test search with non-existent pipeline."""
    resource = FakePipelineResource(get_exception=ResourceNotFoundError())
    client = FakeClient(resource)

    result = await search_pipeline(client=client, workspace="ws", pipeline_name="missing-pipeline", query="test query")

    assert "There is no pipeline named 'missing-pipeline' in workspace 'ws'" in result


@pytest.mark.asyncio
async def test_search_pipeline_search_error() -> None:
    """Test search with API error during search."""
    user = DeepsetUser(user_id="u1", given_name="Alice", family_name="Smith")
    pipeline = DeepsetPipeline(
        pipeline_id="p1",
        name="test-pipeline",
        status="DEPLOYED",
        service_level=PipelineServiceLevel.PRODUCTION,
        created_at=datetime(2023, 1, 1, 12, 0),
        last_edited_at=None,
        created_by=user,
        last_edited_by=None,
        yaml_config="config: test",
    )

    resource = FakePipelineResource(
        get_response=pipeline,
        search_exception=BadRequestError("Search failed"),
    )
    client = FakeClient(resource)

    result = await search_pipeline(client=client, workspace="ws", pipeline_name="test-pipeline", query="test query")

    assert "Failed to search using pipeline 'test-pipeline': Search failed" in result


@pytest.mark.asyncio
async def test_search_pipeline_no_results() -> None:
    """Test search with no results."""
    user = DeepsetUser(user_id="u1", given_name="Alice", family_name="Smith")
    pipeline = DeepsetPipeline(
        pipeline_id="p1",
        name="test-pipeline",
        status="DEPLOYED",
        service_level=PipelineServiceLevel.PRODUCTION,
        created_at=datetime(2023, 1, 1, 12, 0),
        last_edited_at=None,
        created_by=user,
        last_edited_by=None,
        yaml_config="config: test",
    )

    search_response = DeepsetSearchResponse(
        query="No results query",
        answers=[],
        documents=[],
    )

    resource = FakePipelineResource(
        get_response=pipeline,
        search_response=search_response,
    )
    client = FakeClient(resource)

    result = await search_pipeline(
        client=client, workspace="ws", pipeline_name="test-pipeline", query="No results query"
    )

    assert isinstance(result, DeepsetSearchResponse)
    assert result.query == "No results query"
    assert len(result.answers) == 0
    assert len(result.documents) == 0


@pytest.mark.asyncio
async def test_search_pipeline_with_documents() -> None:
    """Test search that returns documents instead of answers."""
    user = DeepsetUser(user_id="u1", given_name="Alice", family_name="Smith")
    pipeline = DeepsetPipeline(
        pipeline_id="p1",
        name="test-pipeline",
        status="DEPLOYED",
        service_level=PipelineServiceLevel.PRODUCTION,
        created_at=datetime(2023, 1, 1, 12, 0),
        last_edited_at=None,
        created_by=user,
        last_edited_by=None,
        yaml_config="config: test",
    )

    document = DeepsetDocument(
        content="This is a test document with some content that should be displayed.",
        meta={"title": "Test Document", "source": "test.txt"},
        score=0.85,
        id="doc1",
    )

    search_response = DeepsetSearchResponse(
        query="test document",
        answers=[],  # No answers, only documents
        documents=[document],
    )

    resource = FakePipelineResource(
        get_response=pipeline,
        search_response=search_response,
    )
    client = FakeClient(resource)

    result = await search_pipeline(client=client, workspace="ws", pipeline_name="test-pipeline", query="test document")

    assert isinstance(result, DeepsetSearchResponse)
    assert result.query == "test document"
    assert len(result.answers) == 0
    assert len(result.documents) == 1
    assert result.documents[0].content == "This is a test document with some content that should be displayed."
    assert result.documents[0].meta["title"] == "Test Document"
