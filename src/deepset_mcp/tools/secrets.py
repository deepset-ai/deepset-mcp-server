from deepset_mcp.api.exceptions import ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.api.secrets.models import Secret, SecretList


async def list_secrets(*, client: AsyncClientProtocol, limit: int = 10) -> SecretList | str:
    """Lists all secrets available in the user's deepset organization.

    Use this tool to retrieve a list of secrets with their names and IDs.
    This is useful for getting an overview of all secrets before retrieving specific ones.

    :param client: The deepset API client
    :param limit: Maximum number of secrets to return (default: 10)

    :returns: List of secrets or error message
    """
    try:
        return await client.secrets().list(limit=limit)
    except ResourceNotFoundError as e:
        return f"Error: {str(e)}"
    except UnexpectedAPIError as e:
        return f"API Error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


async def get_secret(*, client: AsyncClientProtocol, secret_id: str) -> Secret | str:
    """Retrieves detailed information about a specific secret by its ID.

    Use this tool to get information about a specific secret when you know its ID.
    The secret value itself is not returned for security reasons, only metadata.

    :param client: The deepset API client
    :param secret_id: The unique identifier of the secret to retrieve

    :returns: Secret information or error message
    """
    try:
        return await client.secrets().get(secret_id=secret_id)
    except ResourceNotFoundError as e:
        return f"Error: {str(e)}"
    except UnexpectedAPIError as e:
        return f"API Error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"
