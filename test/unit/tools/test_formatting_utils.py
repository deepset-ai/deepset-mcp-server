from datetime import datetime

from deepset_mcp.api.pipeline.models import (
    PipelineLog,
    PipelineLogList,
    PipelineValidationResult,
    ValidationError,
)
from deepset_mcp.tools.formatting_utils import (
    pipeline_logs_to_llm_readable_string,
    validation_result_to_llm_readable_string,
)


def test_pipeline_logs_to_llm_readable_string_with_logs() -> None:
    """Test formatting pipeline logs with data."""
    log1 = PipelineLog(
        log_id="log1",
        message="Pipeline started successfully",
        logged_at=datetime(2023, 1, 1, 12, 0, 0),
        level="info",
        origin="querypipeline",
        exceptions=None,
        extra_fields={},
    )
    log2 = PipelineLog(
        log_id="log2",
        message="Error processing document",
        logged_at=datetime(2023, 1, 1, 12, 1, 30),
        level="error",
        origin="querypipeline",
        exceptions="ValueError: Invalid document format",
        extra_fields={"component": "document_reader", "file_name": "test.pdf"},
    )

    logs = PipelineLogList(data=[log1, log2], has_more=True, total=5)

    result = pipeline_logs_to_llm_readable_string(logs, "test-pipeline")

    # Check basic structure
    assert "### Logs for Pipeline 'test-pipeline'" in result
    assert "**Total Logs:** 5" in result
    assert "**Showing:** 2 entries" in result
    assert "**Has More:** Yes" in result

    # Check log entry 1
    assert "**Log Entry 1**" in result
    assert "**Timestamp:** January 01, 2023 12:00:00 PM" in result
    assert "**Level:** info" in result
    assert "**Origin:** querypipeline" in result
    assert "**Message:** Pipeline started successfully" in result

    # Check log entry 2
    assert "**Log Entry 2**" in result
    assert "**Timestamp:** January 01, 2023 12:01:30 PM" in result
    assert "**Level:** error" in result
    assert "**Message:** Error processing document" in result
    assert "**Exceptions:** ValueError: Invalid document format" in result
    assert "component: document_reader" in result
    assert "file_name: test.pdf" in result

    # Check pagination note
    assert "*Note: There are more log entries available. Adjust the limit parameter to see more.*" in result


def test_pipeline_logs_to_llm_readable_string_empty() -> None:
    """Test formatting empty pipeline logs."""
    logs = PipelineLogList(data=[], has_more=False, total=0)

    result = pipeline_logs_to_llm_readable_string(logs, "empty-pipeline")

    assert result == "No logs found for pipeline 'empty-pipeline'."


def test_pipeline_logs_to_llm_readable_string_empty_with_filter() -> None:
    """Test formatting empty pipeline logs with level filter."""
    logs = PipelineLogList(data=[], has_more=False, total=0)

    result = pipeline_logs_to_llm_readable_string(logs, "test-pipeline", level="error")

    assert result == "No logs found for pipeline 'test-pipeline' (filtered by level: error)."


def test_pipeline_logs_to_llm_readable_string_with_level_filter() -> None:
    """Test formatting pipeline logs with level filter applied."""
    log = PipelineLog(
        log_id="log1",
        message="Critical error",
        logged_at=datetime(2023, 1, 1, 12, 0, 0),
        level="error",
        origin="querypipeline",
        exceptions=None,
        extra_fields={},
    )

    logs = PipelineLogList(data=[log], has_more=False, total=1)

    result = pipeline_logs_to_llm_readable_string(logs, "test-pipeline", level="error")

    assert "### Logs for Pipeline 'test-pipeline'" in result
    assert "**Filter Applied:** Level = error" in result
    assert "**Total Logs:** 1" in result
    assert "**Showing:** 1 entries" in result
    assert "**Has More:** No" in result
    assert "**Message:** Critical error" in result


def test_pipeline_logs_to_llm_readable_string_no_pagination_note() -> None:
    """Test that pagination note is not shown when has_more is False."""
    log = PipelineLog(
        log_id="log1",
        message="Test message",
        logged_at=datetime(2023, 1, 1, 12, 0, 0),
        level="info",
        origin="querypipeline",
        exceptions=None,
        extra_fields={},
    )

    logs = PipelineLogList(data=[log], has_more=False, total=1)

    result = pipeline_logs_to_llm_readable_string(logs, "test-pipeline")

    assert "*Note: There are more log entries available" not in result


def test_validation_result_to_llm_readable_string_valid() -> None:
    """Test formatting valid validation result."""
    result = PipelineValidationResult(valid=True, errors=[])

    formatted = validation_result_to_llm_readable_string(result)

    assert "The provided pipeline configuration is valid." in formatted
    assert "Validation Errors" not in formatted


def test_validation_result_to_llm_readable_string_invalid() -> None:
    """Test formatting invalid validation result."""
    errors = [
        ValidationError(code="YAML_ERROR", message="Syntax error in YAML"),
        ValidationError(code="COMPONENT_ERROR", message="Unknown component type"),
    ]
    result = PipelineValidationResult(valid=False, errors=errors)

    formatted = validation_result_to_llm_readable_string(result)

    assert "The provided pipeline configuration is invalid." in formatted
    assert "**Validation Errors**" in formatted
    assert "Error 1" in formatted
    assert "- Code: YAML_ERROR" in formatted
    assert "- Message: Syntax error in YAML" in formatted
    assert "Error 2" in formatted
    assert "- Code: COMPONENT_ERROR" in formatted
    assert "- Message: Unknown component type" in formatted
