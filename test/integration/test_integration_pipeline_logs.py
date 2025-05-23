import os
import pytest

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.api.pipeline.log_models import PipelineLogList


def skip_if_no_api_key() -> pytest.MarkDecorator:
    """Skip test if no API key is available."""
    return pytest.mark.skipif(
        not os.getenv("DEEPSET_API_KEY"),
        reason="DEEPSET_API_KEY environment variable not set"
    )


class TestIntegrationPipelineLogs:
    """Integration tests for pipeline logs functionality."""

    @skip_if_no_api_key()
    @pytest.mark.asyncio
    async def test_get_logs_integration(self) -> None:
        """Test getting logs from a real pipeline (integration test)."""
        # This test requires a real API key and existing pipeline
        # Skip if not in integration test environment
        workspace = os.getenv("DEEPSET_WORKSPACE", "default")
        pipeline_name = os.getenv("DEEPSET_TEST_PIPELINE")
        
        if not pipeline_name:
            pytest.skip("DEEPSET_TEST_PIPELINE environment variable not set")

        async with AsyncDeepsetClient() as client:
            # Get logs directly from resource
            logs = await client.pipelines(workspace).get_logs(
                pipeline_name=pipeline_name,
                limit=5
            )
            
            # Verify response structure
            assert isinstance(logs, PipelineLogList)
            assert isinstance(logs.data, list)
            assert isinstance(logs.has_more, bool)
            assert isinstance(logs.total, int)
            
            # If there are logs, verify their structure
            if logs.data:
                log = logs.data[0]
                assert hasattr(log, 'log_id')
                assert hasattr(log, 'message')
                assert hasattr(log, 'logged_at')
                assert hasattr(log, 'level')
                assert hasattr(log, 'origin')
                assert log.origin == "querypipeline"  # Should always be querypipeline

    @skip_if_no_api_key()
    @pytest.mark.asyncio
    async def test_get_logs_with_level_filter_integration(self) -> None:
        """Test getting logs with level filter (integration test)."""
        workspace = os.getenv("DEEPSET_WORKSPACE", "default")
        pipeline_name = os.getenv("DEEPSET_TEST_PIPELINE")
        
        if not pipeline_name:
            pytest.skip("DEEPSET_TEST_PIPELINE environment variable not set")

        async with AsyncDeepsetClient() as client:
            # Get pipeline handle
            handle = await client.pipelines(workspace).get(pipeline_name, include_yaml=False)
            
            # Get error logs specifically
            error_logs = await handle.get_logs(limit=10, level="error")
            
            # Verify response structure
            assert isinstance(error_logs, PipelineLogList)
            
            # If there are error logs, verify they are all error level
            if error_logs.data:
                for log in error_logs.data:
                    assert log.level == "error"
                    assert log.origin == "querypipeline"

    @skip_if_no_api_key()
    @pytest.mark.asyncio
    async def test_get_logs_through_resource_integration(self) -> None:
        """Test getting logs directly through resource (integration test)."""
        workspace = os.getenv("DEEPSET_WORKSPACE", "default")
        pipeline_name = os.getenv("DEEPSET_TEST_PIPELINE")
        
        if not pipeline_name:
            pytest.skip("DEEPSET_TEST_PIPELINE environment variable not set")

        async with AsyncDeepsetClient() as client:
            # Get logs directly through resource
            logs = await client.pipelines(workspace).get_logs(
                pipeline_name=pipeline_name,
                limit=3,
                level="info"
            )
            
            # Verify response structure
            assert isinstance(logs, PipelineLogList)
            
            # If there are logs, verify they are all info level
            if logs.data:
                for log in logs.data:
                    assert log.level == "info"
                    assert log.origin == "querypipeline"