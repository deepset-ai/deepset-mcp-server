# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel

from deepset_mcp.api.exceptions import ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.protocols import AsyncClientProtocol


class EnvironmentSecret(BaseModel):
    """Model representing a secret."""

    name: str
    "Human-readable name of the secret"
    id: str
    "Unique identifier for the secret"


class EnvironmentSecretList(BaseModel):
    """Model representing a list of secrets."""

    data: list[EnvironmentSecret]
    "List of secrets for the current page"
    has_more: bool
    "Whether there are more items available beyond this page"
    total: int
    "Total number of secrets"
    next_cursor: str | None = None
    "Cursor for fetching the next page of results"


async def list_secrets(
    *,
    client: AsyncClientProtocol,
    workspace: str | None = None,
    limit: int = 10,
    after: str | None = None,
) -> EnvironmentSecretList | str:
    """Lists all secrets available in the user's deepset organization or in a specific workspace.

    Use this tool to retrieve a list of secrets with their names and IDs.
    This is useful for getting an overview of all secrets before retrieving specific ones.

    :param client: The deepset API client
    :param workspace: Optional workspace name. If provided, lists the secrets available in this workspace.
    :param limit: Maximum number of secrets to return (default: 10)
    :param after: The cursor to fetch the next page of results

    :returns: List of secrets or error message
    """
    try:
        secrets_list = await client.secrets().list(limit=limit, after=after, workspace=workspace)

        env_secrets = [EnvironmentSecret(name=secret.name, id=secret.secret_id) for secret in secrets_list.data]

        return EnvironmentSecretList(
            data=env_secrets,
            has_more=secrets_list.has_more,
            total=len(env_secrets),
            next_cursor=secrets_list.next_cursor,
        )
    except ResourceNotFoundError as e:
        return f"Error: {str(e)}"
    except UnexpectedAPIError as e:
        return f"API Error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


async def get_secret(*, client: AsyncClientProtocol, secret_id: str) -> EnvironmentSecret | str:
    """Retrieves detailed information about a specific secret by its ID.

    Use this tool to get information about a specific secret when you know its ID.
    The secret value itself is not returned for security reasons, only metadata.

    :param client: The deepset API client
    :param secret_id: The unique identifier of the secret to retrieve

    :returns: Secret information or error message
    """
    try:
        secret = await client.secrets().get(secret_id=secret_id)
        return EnvironmentSecret(name=secret.name, id=secret.secret_id)
    except ResourceNotFoundError:
        return f"Error: Secret with ID '{secret_id}' not found."
    except UnexpectedAPIError as e:
        return f"API Error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"
