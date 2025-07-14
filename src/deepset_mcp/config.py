# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""This module contains static configuration for the deepset MCP server."""

from deepset_mcp import __version__

# We need this mapping to which environment variables integrations are mapped to
# The mapping is maintained in the pipeline operator:
# https://github.com/deepset-ai/dc-pipeline-operator/blob/main/dc_operators/config.py#L279
TOKEN_DOMAIN_MAPPING = {
    "huggingface.co": ["HF_API_TOKEN", "HF_TOKEN"],
    "api.openai.com": ["OPENAI_API_KEY"],
    "bedrock.amazonaws.com": ["BEDROCK"],
    "api.cohere.ai": ["COHERE_API_KEY"],
    "openai.azure.com": ["AZURE_OPENAI_API_KEY"],
    "cognitive-services.azure.com": ["AZURE_AI_API_KEY"],
    "unstructured.io": ["UNSTRUCTURED_API_KEY"],
    "api.deepl.com": ["DEEPL_API_KEY"],
    "generativelanguage.googleapis.com": ["GOOGLE_API_KEY"],
    "api.nvidia.com": ["NVIDIA_API_KEY"],
    "api.voyageai.com": ["VOYAGE_API_KEY"],
    "searchapi.io": ["SEARCHAPI_API_KEY"],
    "snowflakecomputing.com": ["SNOWFLAKE_API_KEY"],
    "wandb.ai": ["WANDB_API_KEY"],
    "mongodb.com": ["MONGO_CONNECTION_STRING"],
    "together.ai": ["TOGETHERAI_API_KEY"],
}

DEEPSET_DOCS_DEFAULT_SHARE_URL = "https://cloud.deepset.ai/shared_prototypes?share_token=prototype_eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODM0MjE0OTguNTk5LCJhdWQiOiJleHRlcm5hbCB1c2VyIiwiaXNzIjoiZEMiLCJ3b3Jrc3BhY2VfaWQiOiI4YzI0ZjExMi1iMjljLTQ5MWMtOTkzOS1hZTkxMDRhNTQyMWMiLCJ3b3Jrc3BhY2VfbmFtZSI6ImRjLWRvY3MtY29udGVudCIsIm9yZ2FuaXphdGlvbl9pZCI6ImNhOWYxNGQ0LWMyYzktNDYwZC04ZDI2LWY4Y2IwYWNhMDI0ZiIsInNoYXJlX2lkIjoiY2Y3MTA3ODAtOThmNi00MzlmLThiNzYtMmMwNDkyODNiMDZhIiwibG9naW5fcmVxdWlyZWQiOmZhbHNlfQ.5j6DCNRQ1_KB8lhIJqHyw2hBIleEW1_Y_UBuH6MTYY0"

DEFAULT_CLIENT_HEADER = {"headers": {"User-Agent": f"deepset-mcp/{__version__}"}}
