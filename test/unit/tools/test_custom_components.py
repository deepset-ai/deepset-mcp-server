import pytest

from deepset_mcp.api.custom_components.models import (
    CustomComponentInstallation,
    CustomComponentInstallationList,
)
from deepset_mcp.api.exceptions import UnexpectedAPIError
from deepset_mcp.api.shared_models import DeepsetUser
from deepset_mcp.tools.custom_components import (
    get_latest_custom_component_installation_logs,
    list_custom_component_installations,
)
from test.unit.conftest import BaseFakeClient


class FakeCustomComponentsResource:
    def __init__(
        self,
        installations_response: CustomComponentInstallationList | None = None,
        latest_logs_response: str | None = None,
        exception: Exception | None = None,
    ):
        self._installations_response = installations_response
        self._latest_logs_response = latest_logs_response
        self._exception = exception

    async def list_installations(
        self, limit: int = 20, page_number: int = 1, field: str = "created_at", order: str = "DESC"
    ) -> CustomComponentInstallationList:
        if self._exception:
            raise self._exception
        if self._installations_response is not None:
            return self._installations_response
        raise NotImplementedError

    async def get_latest_installation_logs(self) -> str | None:
        if self._exception:
            raise self._exception
        return self._latest_logs_response


class FakeUserResource:
    def __init__(
        self,
        users: dict[str, DeepsetUser] | None = None,
        exception: Exception | None = None,
    ):
        self._users = users or {}
        self._exception = exception

    async def get(self, user_id: str) -> DeepsetUser:
        if self._exception:
            raise self._exception
        if user_id in self._users:
            return self._users[user_id]
        raise Exception("User not found")


class FakeClient(BaseFakeClient):
    def __init__(
        self,
        custom_components_resource: FakeCustomComponentsResource | None = None,
        user_resource: FakeUserResource | None = None,
    ):
        self._custom_components_resource = custom_components_resource
        self._user_resource = user_resource
        super().__init__()

    def custom_components(self, workspace: str) -> FakeCustomComponentsResource:
        if self._custom_components_resource is None:
            raise ValueError("Custom components resource not configured")
        return self._custom_components_resource

    def users(self) -> FakeUserResource:
        if self._user_resource is None:
            raise ValueError("User resource not configured")
        return self._user_resource


@pytest.mark.asyncio
async def test_list_custom_component_installations() -> None:
    """Test listing custom component installations."""
    mock_installations = CustomComponentInstallationList(
        data=[
            CustomComponentInstallation(
                custom_component_id="comp_123",
                status="installed",
                version="1.0.0",
                created_by_user_id="user_123",
                organization_id="org-123",
                logs=[{"level": "INFO", "msg": "Installation complete"}],
            ),
            CustomComponentInstallation(
                custom_component_id="comp_456",
                status="failed",
                version="0.9.0",
                created_by_user_id="user_456",
                organization_id="org-456",
                logs=[
                    {"level": "ERROR", "msg": "Installation failed"},
                    {"level": "DEBUG", "msg": "Debug info"},
                ],
            ),
        ],
        total=2,
        has_more=False,
    )

    mock_users = {
        "user_123": DeepsetUser(
            user_id="user_123",
            given_name="John",
            family_name="Doe",
            email="john.doe@example.com",
        ),
        "user_456": DeepsetUser(
            user_id="user_456",
            given_name="Jane",
            family_name="Smith",
            email="jane.smith@example.com",
        ),
    }

    custom_components_resource = FakeCustomComponentsResource(installations_response=mock_installations)
    user_resource = FakeUserResource(users=mock_users)
    client = FakeClient(
        custom_components_resource=custom_components_resource,
        user_resource=user_resource,
    )

    result = await list_custom_component_installations(client, "test-workspace")

    assert "# Custom Component Installations (showing 2 of 2)" in result
    assert "## Installation comp_123..." in result
    assert "## Installation comp_456..." in result
    assert "**Status**: installed" in result
    assert "**Status**: failed" in result
    assert "**Version**: 1.0.0" in result
    assert "**Version**: 0.9.0" in result
    assert "**Installed by**: John Doe (john.doe@example.com)" in result
    assert "**Installed by**: Jane Smith (jane.smith@example.com)" in result
    assert "[INFO] Installation complete" in result
    assert "[ERROR] Installation failed" in result
    assert "[DEBUG] Debug info" in result


@pytest.mark.asyncio
async def test_list_custom_component_installations_empty() -> None:
    """Test listing custom component installations when none exist."""
    mock_installations = CustomComponentInstallationList(
        data=[],
        total=0,
        has_more=False,
    )

    custom_components_resource = FakeCustomComponentsResource(installations_response=mock_installations)
    user_resource = FakeUserResource()
    client = FakeClient(
        custom_components_resource=custom_components_resource,
        user_resource=user_resource,
    )

    result = await list_custom_component_installations(client, "test-workspace")

    assert result == "No custom component installations found."


@pytest.mark.asyncio
async def test_list_custom_component_installations_user_fetch_error() -> None:
    """Test listing custom component installations when user fetch fails."""
    mock_installations = CustomComponentInstallationList(
        data=[
            CustomComponentInstallation(
                custom_component_id="comp_123",
                status="installed",
                organization_id="org-123",
                version="1.0.0",
                created_by_user_id="user_unknown",
                logs=[],
            ),
        ],
        total=1,
        has_more=False,
    )

    custom_components_resource = FakeCustomComponentsResource(installations_response=mock_installations)
    user_resource = FakeUserResource(exception=Exception("User not found"))
    client = FakeClient(
        custom_components_resource=custom_components_resource,
        user_resource=user_resource,
    )

    result = await list_custom_component_installations(client, "test-workspace")

    assert "**Installed by**: Unknown" in result


@pytest.mark.asyncio
async def test_list_custom_component_installations_api_error() -> None:
    """Test listing custom component installations when API fails."""
    custom_components_resource = FakeCustomComponentsResource(exception=Exception("API Error"))
    user_resource = FakeUserResource()
    client = FakeClient(
        custom_components_resource=custom_components_resource,
        user_resource=user_resource,
    )

    result = await list_custom_component_installations(client, "test-workspace")

    assert result == "Failed to retrieve custom component installations: API Error"


@pytest.mark.asyncio
async def test_get_latest_custom_component_installation_logs() -> None:
    """Test getting latest custom component installation logs."""
    mock_logs = "Installation started\nInstalling dependencies\nInstallation complete"

    custom_components_resource = FakeCustomComponentsResource(latest_logs_response=mock_logs)
    client = FakeClient(custom_components_resource=custom_components_resource)

    result = await get_latest_custom_component_installation_logs(client, "test-workspace")

    assert result == f"Latest custom component installation logs:\n\n{mock_logs}"


@pytest.mark.asyncio
async def test_get_latest_custom_component_installation_logs_empty() -> None:
    """Test getting latest custom component installation logs when none exist."""
    custom_components_resource = FakeCustomComponentsResource(latest_logs_response=None)
    client = FakeClient(custom_components_resource=custom_components_resource)

    result = await get_latest_custom_component_installation_logs(client, "test-workspace")

    assert result == "No installation logs found."


@pytest.mark.asyncio
async def test_get_latest_custom_component_installation_logs_api_error() -> None:
    """Test getting latest custom component installation logs when API fails."""
    custom_components_resource = FakeCustomComponentsResource(exception=UnexpectedAPIError("API Error"))
    client = FakeClient(custom_components_resource=custom_components_resource)

    with pytest.raises(UnexpectedAPIError):
        await get_latest_custom_component_installation_logs(client, "test-workspace")
