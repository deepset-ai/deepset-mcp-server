from deepset_mcp.api.protocols import AsyncClientProtocol


async def list_custom_component_installations(client: AsyncClientProtocol, workspace: str) -> str:
    """List custom component installations.

    :param client: The API client to use.
    :param workspace: The workspace to operate in.

    :returns: A formatted string containing installation information.
    """
    custom_components = client.custom_components(workspace)
    users = client.users()

    try:
        installations = await custom_components.list_installations()
    except Exception as e:
        return f"Failed to retrieve custom component installations: {e}"

    if not installations.data:
        return "No custom component installations found."

    # Format the response
    formatted_output = [
        f"# Custom Component Installations (showing {len(installations.data)} of {installations.total})\n"
    ]

    for install in installations.data:
        # Try to fetch user information
        user_info = "Unknown"
        if install.created_by_user_id:
            try:
                user = await users.get(install.created_by_user_id)
                given_name = user.given_name or ""
                family_name = user.family_name or ""
                email = user.email or ""
                user_info = f"{given_name} {family_name} ({email})" if email else f"{given_name} {family_name}"
                user_info = user_info.strip()
                if not user_info:
                    user_info = "Unknown"
            except Exception:
                user_info = "Unknown"

        # Format installation details
        install_details = [
            f"## Installation {install.custom_component_id[:8]}...",
            f"- **Status**: {install.status}",
            f"- **Version**: {install.version}",
            f"- **Installed by**: {user_info}",
            f"- **Created at**: {install.created_at}",
        ]

        # Add logs if available
        if install.logs:
            install_details.append("\n### Recent Logs:")
            for log in install.logs[:5]:  # Show only the first 5 logs
                level = log.get("level", "INFO")
                msg = log.get("msg", "No message")
                install_details.append(f"- [{level}] {msg}")

            if len(install.logs) > 5:
                install_details.append(f"- ... and {len(install.logs) - 5} more log entries")

        formatted_output.append("\n".join(install_details) + "\n")

    if installations.has_more:
        formatted_output.append(
            "*Note: There are more installations available. This listing shows only the most recent.*"
        )

    # Join all sections and return
    return "\n".join(formatted_output)


async def get_latest_custom_component_installation_logs(client: AsyncClientProtocol, workspace: str) -> str:
    """Get the logs from the latest custom component installation.

    :param client: The API client to use.
    :param workspace: The workspace to operate in.

    :returns: A formatted string containing the latest installation logs.
    """
    custom_components = client.custom_components(workspace)

    try:
        logs = await custom_components.get_latest_installation_logs()
    except Exception as e:
        return f"Failed to retrieve latest installation logs: {e}"

    if not logs:
        return "No installation logs found."

    return f"Latest custom component installation logs:\n\n{logs}"
