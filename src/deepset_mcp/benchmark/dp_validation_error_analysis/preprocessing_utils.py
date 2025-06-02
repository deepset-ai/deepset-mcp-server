import pandas as pd


def rename_common_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename common columns in metabase export."""
    return df.rename(
        columns={
            "ID": "event_id",
            "Pipeline Name": "pipeline_name",
            "Source": "event_source",
            "User ID": "user_id",
            "Event Text": "event_text",
            "Organization Name": "organization_name",
            "Deepset User": "is_deepset_user",
            "Deepset Orga": "is_deepset_org",
            "Original Timestamp": "event_timestamp",
            "Workspace Name": "workspace_name",
            "Workspace ID": "workspace_id",
            "Organization ID": "organization_id",
            "Organization Type": "organization_type",
            "User Email": "user_email",
            "Environment": "environment",
            "Pipeline ID": "pipeline_id",
        }
    )


def drop_common_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Drop unnecessary columns from the dataframe."""
    return df.drop(
        columns=[
            "Context Library Name",
            "Context Library Version",
            "Event",
            "Received At",
            "UUID Ts",
            "Timestamp",
            "Sent At",
            "Deepset Cloud Version",
            "Is External User",
        ],
        errors="ignore",
    )


def classify_error_message(error_message: str, error_classes: dict[str, list[str]]) -> str:
    """
    Classify an error message based on substring matching.

    Args:
        error_message (str): The error message to classify
        error_classes (dict): Dictionary mapping error class names to lists of substrings

    Returns:
        str: The error class name or "other" if no match found
    """
    if pd.isna(error_message):
        return "not_available"

    error_message_lower = str(error_message).lower()

    # Check each error class
    for error_class, substrings in error_classes.items():
        for substring in substrings:
            if substring.lower() in error_message_lower:
                return error_class

    return "other"


def add_error_class_column(
    df: pd.DataFrame, error_message_col: str = "error_message", error_classes: dict[str, list[str]] | None = None
) -> pd.DataFrame:
    """
    Add an error_class column to a dataframe based on substring matching.

    Args:
        df (pd.DataFrame): The dataframe to modify
        error_message_col (str): Name of the column containing error messages
        error_classes (dict): Dictionary mapping error class names to lists of substrings

    Returns:
        pd.DataFrame: The dataframe with added error_class column
    """
    if error_classes is None:
        error_classes = {
            "embeddings": [
                "The embedding model",
                "embedding dimension",
                "No embedding model found in indexing pipeline",
                "No embedding model found in index",
            ],
            "index_inputs_outputs": [
                "files input",
                "the input 'files'",
                "Indexing pipelines must start with a 'FilesInput'",
                "must receive files input.",
                "Indexing Pipeline YAMLs should not have outputs.",
                "must define a 'DocumentWriter'",
            ],
            "credentials": [
                "credentials",
                "OpenAI API token was provided",
                "No API key provided.",
                "You are trying to access a gated repo.",
                "Invalid API key",
                "The api_key client option must be set either by passing api_key to the client or by setting the"
                " TOGETHER_API_KEY environment variable",
                "None of the following authentication environment variables are set",
                "Could not connect to Amazon Bedrock. Make sure the AWS environment is configured correctly.",
                "Unknown secret type",
                "Please provide an Azure endpoint",
                "AZURE_OPENAI_ENDPOINT",
                "Unable to authenticate your request",
                "Unable to find your project",
                "Unsupported region for Vertex AI",
                "Could not auto-detect model family",
                "Unknown Hugging Face API type",
                "Unknown api_type",
                "`model_family` parameter must be one of",
            ],
            "custom_components": [
                "dc_custom_component",
            ],
            "pipeline_inputs_outputs": ["needs to output documents and/or answers", "receive the input 'query'"],
            "document_store_configuration": [
                "Connect a valid document store",
                "Pipeline index with name",
                "incorrectly configured document store",
                "Missing 'document_store' in serialization data",
            ],
            "models": [
                "not found on Hugging Face",
                " parameters. Please, use a model with less than ",
                "To use the Serverless Inference API, you need to specify the `model` parameter",
                "is not a valid DeepsetNVIDIAEmbeddingModels",
            ],
            "templating": [
                "There are configuration errors in the 'PromptBuilder'",
                "not found among inputs or outputs of component 'prompt_builder'",
                "There are configuration errors in the 'ChatPromptBuilder'",
                "component of type 'ChatPromptBuilder'",
                "Prompt must have at least one variable. No variables found in the prompt.",
                "Unexpected end of template. Jinja was looking for",
                "No filter named",
                "Jinja was looking for the following tags",
                "Jinja",
                "unknown tag",
                "Invalid template",
                "OutputAdapter",
                "ConditionalRouter",
                "PromptBuilder",
            ],
            "pipeline_connections": [
                "their declared input and output types do not match",
                "does not exist. Input connections of",
                "does not exist. Output connections of",
                "is already connected to",
                "not found among inputs or outputs of component",
                "not found among components who receive inputs or produce outputs",
                "Missing receiver in connection",
                "already connected to",
                "Connecting a Component to itself is not supported",
                "Ensure the output type is",
            ],
            "not_imported": [
                "not imported",
                "Could not import class",
                "Could not locate the module",
                "Could not import",
            ],
            "component_not_found": ["not found in the pipeline."],
            "missing_packages": ["pip install"],
            "wrong_init_param": [
                "__init__() got an unexpected keyword argument",
                "__init__() missing",
                "takes no arguments",
                "cannot be None or empty string",
                "must be set",
                "argument of type 'NoneType' is not iterable",
            ],
            "component_device": ["ComponentDevice", "component device type"],
            "tools": [
                "The value of 'tools' is not a list",
                "Serialized tool",
                "ToolInvoker requires at least one tool",
                "ToolInvoker requires at least one tool to be provided",
                "is not a subclass of Tool",
                "Duplicate tool names found",
                "Error: `data`",
            ],
            "component_type_missing": [
                "Missing 'type' in component",
                "Missing 'type' in",
                "not enough values to unpack (expected 2, got 1)",
            ],
            "serialization": [
                "Couldn't deserialize component",
                "Failed to validate component",
                "Possible reasons include malformed serialized data",
                "string indices must be integers, not 'str'",
                "Couldn't deserialize",
                "can't be deserialized as",
            ],
        }

    # Create a copy to avoid modifying the original dataframe
    df_result = df.copy()

    # Apply the classification function
    df_result["error_class"] = df_result[error_message_col].apply(lambda x: classify_error_message(x, error_classes))

    return df_result
