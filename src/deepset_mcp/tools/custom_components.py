# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from deepset_mcp.api.custom_components.models import CustomComponentInstallationList
from deepset_mcp.api.protocols import AsyncClientProtocol


async def list_custom_component_installations(
    *, client: AsyncClientProtocol, workspace: str
) -> CustomComponentInstallationList | str:
    """List custom component installations.

    :param client: The API client to use.
    :param workspace: The workspace to operate in.

    :returns: Custom component installations or error message.
    """
    custom_components = client.custom_components(workspace)
    users = client.users()

    try:
        installations = await custom_components.list_installations()
    except Exception as e:
        return f"Failed to retrieve custom component installations: {e}"

    # Enrich installations with user information
    for installation in installations.data:
        if installation.created_by_user_id:
            try:
                user = await users.get(installation.created_by_user_id)
                installation.user_info = user
            except Exception:
                # If user fetch fails, user_info remains None
                pass

    return installations


async def get_latest_custom_component_installation_logs(*, client: AsyncClientProtocol, workspace: str) -> str:
    """Get the logs from the latest custom component installation.

    :param client: The API client to use.
    :param workspace: The workspace to operate in.

    :returns: The latest installation logs or error message.
    """
    custom_components = client.custom_components(workspace)

    try:
        logs = await custom_components.get_latest_installation_logs()
        if not logs:
            return "No installation logs found."
        return logs
    except Exception as e:
        return f"Failed to retrieve latest installation logs: {e}"
