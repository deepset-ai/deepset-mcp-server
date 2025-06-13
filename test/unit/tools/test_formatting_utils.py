from datetime import datetime

from uuid import uuid4

from deepset_mcp.api.pipeline.models import (
    DeepsetAnswer,
    DeepsetDocument,
    DeepsetSearchResponse,
    ExceptionInfo,
    PipelineLog,
    PipelineLogList,
    PipelineValidationResult,
    ValidationError,
)
from deepset_mcp.tools.formatting_utils import (
    pipeline_logs_to_llm_readable_string,
    search_response_to_llm_readable_string,
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
        exceptions=[ExceptionInfo(type="bla", value="bla", trace=[])],
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
    assert "**Exceptions:**" in result
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


def test_search_response_to_llm_readable_string_with_answers() -> None:
    """Test formatting search response with answers."""
    answer1 = DeepsetAnswer(
        answer="The capital of France is Paris.",
        score=0.95,
        context="France is a country in Europe. Its capital city is Paris.",
        document_id="doc1",
        meta={"source": "geography.txt", "page": 42},
    )
    answer2 = DeepsetAnswer(
        answer="Paris has a population of about 2.2 million.",
        score=0.88,
        context="Population statistics for major cities.",
    )
    
    query_id = uuid4()
    response = DeepsetSearchResponse(
        query="What is the capital of France?",
        query_id=query_id,
        answers=[answer1, answer2],
        documents=[],
    )

    result = search_response_to_llm_readable_string(response, "geography-pipeline")

    # Check basic structure
    assert "### Search Results from Pipeline 'geography-pipeline'" in result
    assert "**Query:** What is the capital of France?" in result
    assert f"**Query ID:** {query_id}" in result
    assert "### Answers" in result

    # Check answer 1
    assert "**Answer 1**" in result
    assert "- **Text:** The capital of France is Paris." in result
    assert "- **Score:** 0.9500" in result
    assert "- **Context:** France is a country in Europe. Its capital city is Paris." in result
    assert "- **Document ID:** doc1" in result
    assert "- **Metadata:**" in result
    assert "  - source: geography.txt" in result
    assert "  - page: 42" in result

    # Check answer 2
    assert "**Answer 2**" in result
    assert "- **Text:** Paris has a population of about 2.2 million." in result
    assert "- **Score:** 0.8800" in result
    assert "- **Context:** Population statistics for major cities." in result


def test_search_response_to_llm_readable_string_with_documents() -> None:
    """Test formatting search response with documents but no answers."""
    doc1 = DeepsetDocument(
        content="This is a long document with lots of content that should be truncated if it exceeds the character limit set for display purposes.",
        meta={"title": "Long Document", "author": "John Doe"},
        score=0.75,
        id="doc1",
    )
    doc2 = DeepsetDocument(
        content="Short document.",
        meta={"title": "Short Document"},
        score=0.60,
        id="doc2",
    )
    
    response = DeepsetSearchResponse(
        query="test query",
        answers=[],  # No answers
        documents=[doc1, doc2],
    )

    result = search_response_to_llm_readable_string(response, "doc-search-pipeline")

    # Check basic structure
    assert "### Search Results from Pipeline 'doc-search-pipeline'" in result
    assert "**Query:** test query" in result
    assert "### Documents" in result
    assert "### Answers" not in result  # Should not show answers section

    # Check document 1 (should be truncated)
    assert "**Document 1**" in result
    assert "- **Content:** This is a long document with lots of content that should be truncated if it exceeds the character limit set for display purposes." in result
    assert "- **Score:** 0.7500" in result
    assert "- **ID:** doc1" in result
    assert "  - title: Long Document" in result
    assert "  - author: John Doe" in result

    # Check document 2
    assert "**Document 2**" in result
    assert "- **Content:** Short document." in result
    assert "- **Score:** 0.6000" in result
    assert "- **ID:** doc2" in result
    assert "  - title: Short Document" in result


def test_search_response_to_llm_readable_string_truncated_content() -> None:
    """Test that long document content gets truncated."""
    long_content = "A" * 600  # 600 characters, should be truncated to 500 + "..."
    doc = DeepsetDocument(
        content=long_content,
        meta={},
    )
    
    response = DeepsetSearchResponse(
        query="test",
        answers=[],
        documents=[doc],
    )

    result = search_response_to_llm_readable_string(response, "test-pipeline")

    # Should be truncated to 500 chars + "..."
    assert "A" * 500 + "..." in result
    assert len([line for line in result.split("\n") if "**Content:**" in line][0]) <= 520  # Account for prefix


def test_search_response_to_llm_readable_string_no_results() -> None:
    """Test formatting search response with no results."""
    response = DeepsetSearchResponse(
        query="no results query",
        answers=[],
        documents=[],
    )

    result = search_response_to_llm_readable_string(response, "empty-pipeline")

    assert result == "No results found for the search query using pipeline 'empty-pipeline'."


def test_search_response_to_llm_readable_string_minimal_data() -> None:
    """Test formatting search response with minimal data."""
    answer = DeepsetAnswer(
        answer="Simple answer",  # Only required field
    )
    
    response = DeepsetSearchResponse(
        answers=[answer],
        documents=[],
    )

    result = search_response_to_llm_readable_string(response, "minimal-pipeline")

    assert "### Search Results from Pipeline 'minimal-pipeline'" in result
    assert "**Answer 1**" in result
    assert "- **Text:** Simple answer" in result
    # Should not include optional fields that are None
    assert "- **Score:**" not in result
    assert "- **Context:**" not in result
    assert "- **Document ID:**" not in result
    assert "- **Metadata:**" not in result


def test_search_response_to_llm_readable_string_answers_and_documents() -> None:
    """Test that when both answers and documents are present, only answers are shown."""
    answer = DeepsetAnswer(answer="Test answer")
    document = DeepsetDocument(content="Test document", meta={})
    
    response = DeepsetSearchResponse(
        query="test",
        answers=[answer],
        documents=[document],
    )

    result = search_response_to_llm_readable_string(response, "test-pipeline")

    assert "### Answers" in result
    assert "### Documents" not in result
    assert "Test answer" in result
    assert "Test document" not in result
