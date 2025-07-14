# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel

from deepset_mcp.api.exceptions import ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.config import TOKEN_DOMAIN_MAPPING


class EnvironmentSecret(BaseModel):
    """Model representing a secret or an integration."""

    name: str
    id: str
    invalid: bool | None = None


class EnvironmentSecretList(BaseModel):
    """Model representing a list of secrets and integrations."""

    data: list[EnvironmentSecret]
    has_more: bool
    total: int


async def list_secrets(*, client: AsyncClientProtocol, limit: int = 10) -> EnvironmentSecretList | str:
    """Lists all secrets available in the user's deepset organization.

    Use this tool to retrieve a list of secrets with their names and IDs.
    This is useful for getting an overview of all secrets before retrieving specific ones.

    :param client: The deepset API client
    :param limit: Maximum number of secrets to return (default: 10)

    :returns: List of secrets or error message
    """
    try:
        secrets_list = await client.secrets().list(limit=limit)
        integrations_list = await client.integrations().list()

        env_secrets = [EnvironmentSecret(name=secret.name, id=secret.secret_id) for secret in secrets_list.data]
        for integration in integrations_list.integrations:
            env_vars = TOKEN_DOMAIN_MAPPING.get(integration.provider_domain, [])
            for env_var in env_vars:
                env_secrets.append(
                    EnvironmentSecret(
                        name=env_var,
                        id=str(integration.model_registry_token_id),
                        invalid=integration.invalid,
                    )
                )

        return EnvironmentSecretList(
            data=env_secrets,
            has_more=secrets_list.has_more,
            total=len(env_secrets),
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
        try:
            integrations_list = await client.integrations().list()
            for integration in integrations_list.integrations:
                if str(integration.model_registry_token_id) == secret_id:
                    env_vars = TOKEN_DOMAIN_MAPPING.get(integration.provider_domain, [])
                    if env_vars:
                        return EnvironmentSecret(
                            name=env_vars[0],
                            id=str(integration.model_registry_token_id),
                            invalid=integration.invalid,
                        )
            return f"Error: Secret with ID '{secret_id}' not found."
        except UnexpectedAPIError as e:
            return f"API Error: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"
    except UnexpectedAPIError as e:
        return f"API Error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"
