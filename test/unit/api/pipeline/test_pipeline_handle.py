from datetime import datetime

import pytest

from deepset_mcp.api.pipeline.handle import PipelineHandle
from deepset_mcp.api.pipeline.models import DeepsetPipeline, PipelineServiceLevel
from deepset_mcp.api.pipeline.resource import PipelineResource
from deepset_mcp.api.shared_models import DeepsetUser
from test.unit.conftest import BaseFakeClient


class DummyClient(BaseFakeClient):
    """Dummy client for testing."""
    pass


@pytest.fixture
def sample_pipeline() -> DeepsetPipeline:
    """Create a sample pipeline for testing."""
    user = DeepsetUser(
        user_id="user-123",
        given_name="Test",
        family_name="User",
        email="test@example.com"
    )
    
    return DeepsetPipeline(
        pipeline_id="test-pipeline-id",
        name="test-pipeline",
        status="DEPLOYED",
        service_level=PipelineServiceLevel.PRODUCTION,
        created_at=datetime(2023, 1, 1, 12, 0),
        last_edited_at=datetime(2023, 1, 2, 12, 0),
        created_by=user,
        last_edited_by=user,
        yaml_config="version: '1.0'\ncomponents: {}"
    )


@pytest.fixture
def pipeline_resource() -> PipelineResource:
    """Create a pipeline resource for testing."""
    client = DummyClient()
    return PipelineResource(client=client, workspace="test-workspace")


class TestPipelineHandle:
    """Tests for the PipelineHandle class."""

    def test_handle_initialization(self, sample_pipeline: DeepsetPipeline, pipeline_resource: PipelineResource) -> None:
        """Test that PipelineHandle initializes correctly."""
        handle = PipelineHandle(pipeline=sample_pipeline, resource=pipeline_resource)
        
        assert handle._pipeline is sample_pipeline
        assert handle._resource is pipeline_resource

    def test_pipeline_property(self, sample_pipeline: DeepsetPipeline, pipeline_resource: PipelineResource) -> None:
        """Test that the pipeline property returns the underlying pipeline."""
        handle = PipelineHandle(pipeline=sample_pipeline, resource=pipeline_resource)
        
        assert handle.pipeline is sample_pipeline

    def test_attribute_proxying(self, sample_pipeline: DeepsetPipeline, pipeline_resource: PipelineResource) -> None:
        """Test that attributes are properly proxied to the underlying pipeline."""
        handle = PipelineHandle(pipeline=sample_pipeline, resource=pipeline_resource)
        
        # Test accessing various attributes through the handle
        assert handle.id == sample_pipeline.id
        assert handle.name == sample_pipeline.name
        assert handle.status == sample_pipeline.status
        assert handle.service_level == sample_pipeline.service_level
        assert handle.created_at == sample_pipeline.created_at
        assert handle.last_updated_at == sample_pipeline.last_updated_at
        assert handle.created_by == sample_pipeline.created_by
        assert handle.last_updated_by == sample_pipeline.last_updated_by
        assert handle.yaml_config == sample_pipeline.yaml_config

    def test_attribute_error_for_missing_attribute(self, sample_pipeline: DeepsetPipeline, pipeline_resource: PipelineResource) -> None:
        """Test that AttributeError is raised for non-existent attributes."""
        handle = PipelineHandle(pipeline=sample_pipeline, resource=pipeline_resource)
        
        with pytest.raises(AttributeError):
            _ = handle.non_existent_attribute

    def test_handle_maintains_pipeline_type(self, sample_pipeline: DeepsetPipeline, pipeline_resource: PipelineResource) -> None:
        """Test that the handle maintains the correct pipeline type."""
        handle = PipelineHandle(pipeline=sample_pipeline, resource=pipeline_resource)
        
        assert isinstance(handle.pipeline, DeepsetPipeline)
        assert handle.pipeline.id == "test-pipeline-id"
        assert handle.pipeline.name == "test-pipeline"

    def test_handle_resource_access(self, sample_pipeline: DeepsetPipeline, pipeline_resource: PipelineResource) -> None:
        """Test that the handle maintains reference to the resource."""
        handle = PipelineHandle(pipeline=sample_pipeline, resource=pipeline_resource)
        
        # The resource should be accessible (for future operations)
        assert handle._resource is pipeline_resource