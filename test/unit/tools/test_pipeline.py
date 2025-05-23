from datetime import datetime

import pytest

from deepset_mcp.api.exceptions import (
    BadRequestError,
    ResourceNotFoundError,
    UnexpectedAPIError,
)
from deepset_mcp.api.pipeline.models import (
    DeepsetPipeline,
    NoContentResponse,
    PipelineServiceLevel,
    PipelineValidationResult,
    ValidationError,
)
from deepset_mcp.api.pipeline.handle import PipelineHandle
from deepset_mcp.api.shared_models import DeepsetUser

# Adjust the import path below to match your project structure
from deepset_mcp.tools.pipeline import (
    create_pipeline,
    get_pipeline,
    list_pipelines,
    update_pipeline,
    validate_pipeline,
)
from test.unit.conftest import BaseFakeClient


class FakePipelineResource:
    def __init__(
        self,
        list_response: list[DeepsetPipeline] | None = None,
        get_response: DeepsetPipeline | None = None,
        validate_response: PipelineValidationResult | None = None,
        create_response: NoContentResponse | None = None,
        update_response: NoContentResponse | None = None,
        get_exception: Exception | None = None,
        update_exception: Exception | None = None,
        create_exception: Exception | None = None,
    ) -> None:
        self._list_response = list_response
        self._get_response = get_response
        self._validate_response = validate_response
        self._create_response = create_response
        self._create_exception = create_exception
        self._update_response = update_response
        self._get_exception = get_exception
        self._update_exception = update_exception

    async def list(self, page_number: int = 1, limit: int = 10) -> list[PipelineHandle]:
        if self._list_response is not None:
            # Convert DeepsetPipeline instances to PipelineHandle
            return [PipelineHandle(pipeline=p, resource=self) for p in self._list_response]
        raise NotImplementedError

    async def get(self, pipeline_name: str) -> PipelineHandle:
        if self._get_exception:
            raise self._get_exception
        if self._get_response is not None:
            return PipelineHandle(pipeline=self._get_response, resource=self)
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


class FakeClient(BaseFakeClient):
    def __init__(self, resource: FakePipelineResource) -> None:
        self._resource = resource
        super().__init__()

    def pipelines(self, workspace: str) -> FakePipelineResource:
        return self._resource


@pytest.mark.asyncio
async def test_list_pipelines_returns_formatted_string() -> None:
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
    result = await list_pipelines(client, workspace="ws1")
    assert result.count("<pipeline name=") == 2
    assert "pipeline1" in result
    assert "pipeline2" in result


@pytest.mark.asyncio
async def test_get_pipeline_returns_formatted_string() -> None:
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
    result = await get_pipeline(client, workspace="ws2", pipeline_name="mypipe")
    assert "mypipe" in result
    assert "foo: bar" in result


@pytest.mark.asyncio
async def test_validate_pipeline_empty_yaml_returns_message() -> None:
    client = FakeClient(FakePipelineResource())
    result = await validate_pipeline(client, workspace="ws", yaml_configuration="   ")
    assert result == "You need to provide a YAML configuration to validate."


@pytest.mark.asyncio
async def test_validate_pipeline_invalid_yaml_returns_error() -> None:
    client = FakeClient(FakePipelineResource())
    invalid_yaml = "invalid: : yaml"
    result = await validate_pipeline(client, workspace="ws", yaml_configuration=invalid_yaml)
    assert result.startswith("Invalid YAML provided:")


@pytest.mark.asyncio
async def test_validate_pipeline_validates_via_client_and_formats() -> None:
    valid_result = PipelineValidationResult(valid=True, errors=[])
    invalid_result = PipelineValidationResult(
        valid=False,
        errors=[ValidationError(code="E1", message="Oops"), ValidationError(code="E2", message="Bad")],
    )
    # Test valid
    resource_valid = FakePipelineResource(validate_response=valid_result)
    client_valid = FakeClient(resource_valid)
    res_valid = await validate_pipeline(client_valid, workspace="ws", yaml_configuration="a: b")
    assert "configuration is valid" in res_valid
    # Test invalid
    resource_invalid = FakePipelineResource(validate_response=invalid_result)
    client_invalid = FakeClient(resource_invalid)
    res_invalid = await validate_pipeline(client_invalid, workspace="ws", yaml_configuration="a: b")
    assert "configuration is invalid" in res_invalid
    assert "Error 1" in res_invalid
    assert "Error 2" in res_invalid


@pytest.mark.asyncio
async def test_create_pipeline_handles_validation_failure() -> None:
    invalid_result = PipelineValidationResult(valid=False, errors=[ValidationError(code="E", message="Err")])
    resource = FakePipelineResource(validate_response=invalid_result)
    client = FakeClient(resource)
    result = await create_pipeline(client, workspace="ws", pipeline_name="pname", yaml_configuration="cfg")
    assert "invalid" in result.lower()
    assert "Error 1" in result


@pytest.mark.asyncio
async def test_create_pipeline_handles_success_and_failure_response() -> None:
    valid_result = PipelineValidationResult(valid=True, errors=[])

    # success
    resource_succ = FakePipelineResource(
        validate_response=valid_result,
        create_response=NoContentResponse(message="created successfully"),
    )
    client_succ = FakeClient(resource_succ)
    res_succ = await create_pipeline(client_succ, workspace="ws", pipeline_name="p1", yaml_configuration="a: b")

    assert "created successfully" in res_succ
    # failure
    resource_fail = FakePipelineResource(
        validate_response=valid_result,
        create_exception=BadRequestError(message="bad things"),
    )
    client_fail = FakeClient(resource_fail)
    res_fail = await create_pipeline(client_fail, workspace="ws", pipeline_name="p1", yaml_configuration="a: b")
    assert "Failed to create pipeline 'p1': bad things (Status Code: 400)" == res_fail


@pytest.mark.asyncio
async def test_update_pipeline_not_found_on_get() -> None:
    resource = FakePipelineResource(get_exception=ResourceNotFoundError())
    client = FakeClient(resource)
    res = await update_pipeline(
        client, workspace="ws", pipeline_name="np", original_config_snippet="x", replacement_config_snippet="y"
    )
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
        client, workspace="ws", pipeline_name="np", original_config_snippet="baz", replacement_config_snippet="qux"
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
        client, workspace="ws", pipeline_name="np", original_config_snippet="dup: x", replacement_config_snippet="z"
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
        client,
        workspace="ws",
        pipeline_name="np",
        original_config_snippet="foo: 1",
        replacement_config_snippet="foo: 2",
    )
    assert "invalid" in res.lower()
    assert "Error 1" in res


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
        client_not_found,
        workspace="ws",
        pipeline_name="np",
        original_config_snippet="foo: 1",
        replacement_config_snippet="foo: 2",
    )
    assert "no pipeline named 'np'" in r1.lower()
    # BadRequestError
    res_bad = FakePipelineResource(
        get_response=original, validate_response=val_ok, update_exception=BadRequestError("bad request")
    )
    client_bad = FakeClient(res_bad)
    r2 = await update_pipeline(
        client_bad,
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
        client_unexp,
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
    val_ok = PipelineValidationResult(valid=True, errors=[])

    # success
    res_succ = FakePipelineResource(
        get_response=original,
        validate_response=val_ok,
        update_response=NoContentResponse(message="successfully updated"),
    )
    client_succ = FakeClient(res_succ)
    r_success = await update_pipeline(
        client_succ,
        workspace="ws",
        pipeline_name="np",
        original_config_snippet="foo: 1",
        replacement_config_snippet="foo: 2",
    )
    assert "successfully updated" in r_success.lower()
