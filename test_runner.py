#!/usr/bin/env python3
"""Simple test runner for verification."""

import asyncio
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from deepset_mcp.tools.haystack_service import search_pipeline_templates
try:
    from test.unit.tools.test_haystack_service import FakeModel, FakePipelineTemplatesResource, FakeClient
except ImportError:
    print("Failed to import test modules - let's test imports directly")
    from deepset_mcp.api.pipeline_template.models import PipelineTemplate as PT
    print(f"PipelineTemplate imported: {PT}")
    sys.exit(1)
from deepset_mcp.api.pipeline_template.models import PipelineTemplate, PipelineType
from uuid import uuid4

async def test_our_implementation():
    """Test our search_pipeline_templates implementation."""
    print("Testing search_pipeline_templates implementation...")
    
    # Create sample pipeline templates
    templates = [
        PipelineTemplate(
            author="Deepset",
            best_for=["Document Q&A"],
            description="A retrieval-augmented generation template for answering questions",
            template_name="rag-pipeline",
            display_name="RAG Pipeline",
            pipeline_template_id=uuid4(),
            potential_applications=["FAQ systems", "Document search"],
            yaml_config="components:\n  retriever: ...\n  generator: ...",
            tags=[],
            pipeline_type=PipelineType.QUERY,
        ),
        PipelineTemplate(
            author="Deepset",
            best_for=["Conversational AI"],
            description="A chat-based conversational pipeline for interactive responses",
            template_name="chat-pipeline",
            display_name="Chat Pipeline",
            pipeline_template_id=uuid4(),
            potential_applications=["Chatbots", "Virtual assistants"],
            yaml_config="components:\n  chat_generator: ...\n  memory: ...",
            tags=[],
            pipeline_type=PipelineType.QUERY,
        ),
    ]

    templates_resource = FakePipelineTemplatesResource(list_templates_response=templates)
    client = FakeClient(templates_resource=templates_resource)
    model = FakeModel()

    # Test 1: Search for RAG templates
    print("\nTest 1: Searching for RAG templates...")
    result = await search_pipeline_templates(client, "retrieval augmented generation", model, "test_workspace")
    assert "rag-pipeline" in result
    assert "Similarity Score:" in result
    print("✓ RAG search test passed")

    # Test 2: Search for chat templates
    print("\nTest 2: Searching for chat templates...")
    result = await search_pipeline_templates(client, "conversational chat interface", model, "test_workspace")
    assert "chat-pipeline" in result
    assert "Similarity Score:" in result
    print("✓ Chat search test passed")

    print("\n✅ All tests passed!")
    return True

def main():
    """Run the tests."""
    try:
        return asyncio.run(test_our_implementation())
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
