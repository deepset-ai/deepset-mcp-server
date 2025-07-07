"""This module contains static configuration for the deepset MCP server."""

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
