#!/usr/bin/env python3
"""Check if our implementation imports correctly."""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from deepset_mcp.tools.haystack_service import search_pipeline_templates
    print("✓ search_pipeline_templates imported successfully")
except Exception as e:
    print(f"❌ Failed to import search_pipeline_templates: {e}")
    sys.exit(1)

try:
    from deepset_mcp.api.pipeline_template.models import PipelineTemplate, PipelineType
    print("✓ PipelineTemplate models imported successfully")
except Exception as e:
    print(f"❌ Failed to import PipelineTemplate models: {e}")
    sys.exit(1)

try:
    from deepset_mcp.tools.formatting_utils import pipeline_template_to_llm_readable_string
    print("✓ formatting utils imported successfully")
except Exception as e:
    print(f"❌ Failed to import formatting utils: {e}")
    sys.exit(1)

print("✅ All imports successful!")
