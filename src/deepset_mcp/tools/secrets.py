from deepset_mcp.api.exceptions import ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.protocols import AsyncClientProtocol


async def list_secrets(client: AsyncClientProtocol, limit: int = 10) -> str:
    """Lists all secrets available in the user's deepset organization.

    Use this tool to retrieve a list of secrets with their names and IDs.
    This is useful for getting an overview of all secrets before retrieving specific ones.

    :param client: The deepset API client
    :param limit: Maximum number of secrets to return (default: 10)

    :returns: A formatted string containing secret names and IDs
    """
    try:
        response = await client.secrets().list(limit=limit)

        if not response.data:
            return "No secrets found in this workspace."

        secrets_info = []
        for secret in response.data:
            secrets_info.append(f"Name: {secret.name}, ID: {secret.secret_id}")

        result = f"Found {len(response.data)} secret(s):\n" + "\n".join(secrets_info)

        if response.has_more:
            result += (
                f"\n\nShowing {len(response.data)} of {response.total} total secrets. Use a higher limit to see more."
            )

        return result

    except ResourceNotFoundError as e:
        return f"Error: {str(e)}"
    except UnexpectedAPIError as e:
        return f"API Error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


async def get_secret(client: AsyncClientProtocol, secret_id: str) -> str:
    """Retrieves detailed information about a specific secret by its ID.

    Use this tool to get information about a specific secret when you know its ID.
    The secret value itself is not returned for security reasons, only metadata.

    :param client: The deepset API client
    :param secret_id: The unique identifier of the secret to retrieve

    :returns: A formatted string containing secret information
    """
    try:
        response = await client.secrets().get(secret_id)

        return f"Secret Details:\nName: {response.name}\nID: {response.secret_id}"

    except ResourceNotFoundError as e:
        return f"Error: {str(e)}"
    except UnexpectedAPIError as e:
        return f"API Error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"
