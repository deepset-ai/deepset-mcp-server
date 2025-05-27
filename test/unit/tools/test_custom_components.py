import pytest

from deepset_mcp.api.custom_components.models import (
    CustomComponentInstallation,
    CustomComponentInstallationList,
)
from deepset_mcp.api.custom_components.resource import CustomComponentsResource
from deepset_mcp.api.shared_models import DeepsetUser
from deepset_mcp.api.user.resource import UserResource
from deepset_mcp.tools.custom_components import (
    get_latest_custom_component_installation_logs,
    list_custom_component_installations,
)
from test.unit.conftest import BaseFakeClient


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
                created_at="2024-01-01T00:00:00Z",
                logs=[{"level": "INFO", "msg": "Installation complete"}],
            ),
            CustomComponentInstallation(
                custom_component_id="comp_456",
                status="failed",
                version="0.9.0",
                created_by_user_id="user_456",
                created_at="2024-01-02T00:00:00Z",
                logs=[
                    {"level": "ERROR", "msg": "Installation failed"},
                    {"level": "DEBUG", "msg": "Debug info"},
                ],
            ),
        ],
        total=2,
        has_more=False,
    )

    mock_user_123 = DeepsetUser(
        id="user_123",
        given_name="John",
        family_name="Doe",
        email="john.doe@example.com",
    )

    mock_user_456 = DeepsetUser(
        id="user_456",
        given_name="Jane",
        family_name="Smith",
        email="jane.smith@example.com",
    )

    class FakeCustomComponentsResource(CustomComponentsResource):
        async def list_installations(self, limit=20, page_number=1, field="created_at", order="DESC"):
            return mock_installations

        async def get_latest_installation_logs(self):
            return "mock logs"

    class FakeUserResource(UserResource):
        async def get(self, user_id):
            if user_id == "user_123":
                return mock_user_123
            elif user_id == "user_456":
                return mock_user_456
            raise Exception("User not found")

    fake_client = BaseFakeClient()
    fake_client.custom_components = lambda workspace: FakeCustomComponentsResource(fake_client)
    fake_client.users = lambda: FakeUserResource(fake_client)

    result = await list_custom_component_installations(fake_client, "test-workspace")

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

    class FakeCustomComponentsResource(CustomComponentsResource):
        async def list_installations(self, limit=20, page_number=1, field="created_at", order="DESC"):
            return mock_installations

        async def get_latest_installation_logs(self):
            return "mock logs"

    fake_client = BaseFakeClient()
    fake_client.custom_components = lambda workspace: FakeCustomComponentsResource(fake_client)
    fake_client.users = lambda: UserResource(fake_client)

    result = await list_custom_component_installations(fake_client, "test-workspace")

    assert result == "No custom component installations found."


@pytest.mark.asyncio
async def test_list_custom_component_installations_user_fetch_error() -> None:
    """Test listing custom component installations when user fetch fails."""
    mock_installations = CustomComponentInstallationList(
        data=[
            CustomComponentInstallation(
                custom_component_id="comp_123",
                status="installed",
                version="1.0.0",
                created_by_user_id="user_unknown",
                created_at="2024-01-01T00:00:00Z",
                logs=[],
            ),
        ],
        total=1,
        has_more=False,
    )

    class FakeCustomComponentsResource(CustomComponentsResource):
        async def list_installations(self, limit=20, page_number=1, field="created_at", order="DESC"):
            return mock_installations

        async def get_latest_installation_logs(self):
            return "mock logs"

    class FakeUserResource(UserResource):
        async def get(self, user_id):
            raise Exception("User not found")

    fake_client = BaseFakeClient()
    fake_client.custom_components = lambda workspace: FakeCustomComponentsResource(fake_client)
    fake_client.users = lambda: FakeUserResource(fake_client)

    result = await list_custom_component_installations(fake_client, "test-workspace")

    assert "**Installed by**: Unknown" in result


@pytest.mark.asyncio
async def test_list_custom_component_installations_api_error() -> None:
    """Test listing custom component installations when API fails."""
    class FakeCustomComponentsResource(CustomComponentsResource):
        async def list_installations(self, limit=20, page_number=1, field="created_at", order="DESC"):
            raise Exception("API Error")

        async def get_latest_installation_logs(self):
            return "mock logs"

    fake_client = BaseFakeClient()
    fake_client.custom_components = lambda workspace: FakeCustomComponentsResource(fake_client)
    fake_client.users = lambda: UserResource(fake_client)

    result = await list_custom_component_installations(fake_client, "test-workspace")

    assert result == "Failed to retrieve custom component installations: API Error"


@pytest.mark.asyncio
async def test_get_latest_custom_component_installation_logs() -> None:
    """Test getting latest custom component installation logs."""
    mock_logs = "Installation started\nInstalling dependencies\nInstallation complete"

    class FakeCustomComponentsResource(CustomComponentsResource):
        async def list_installations(self, limit=20, page_number=1, field="created_at", order="DESC"):
            return CustomComponentInstallationList(data=[], total=0, has_more=False)

        async def get_latest_installation_logs(self):
            return mock_logs

    fake_client = BaseFakeClient()
    fake_client.custom_components = lambda workspace: FakeCustomComponentsResource(fake_client)

    result = await get_latest_custom_component_installation_logs(fake_client, "test-workspace")

    assert result == f"Latest custom component installation logs:\n\n{mock_logs}"


@pytest.mark.asyncio
async def test_get_latest_custom_component_installation_logs_empty() -> None:
    """Test getting latest custom component installation logs when none exist."""
    class FakeCustomComponentsResource(CustomComponentsResource):
        async def list_installations(self, limit=20, page_number=1, field="created_at", order="DESC"):
            return CustomComponentInstallationList(data=[], total=0, has_more=False)

        async def get_latest_installation_logs(self):
            return None

    fake_client = BaseFakeClient()
    fake_client.custom_components = lambda workspace: FakeCustomComponentsResource(fake_client)

    result = await get_latest_custom_component_installation_logs(fake_client, "test-workspace")

    assert result == "No installation logs found."


@pytest.mark.asyncio
async def test_get_latest_custom_component_installation_logs_api_error() -> None:
    """Test getting latest custom component installation logs when API fails."""
    class FakeCustomComponentsResource(CustomComponentsResource):
        async def list_installations(self, limit=20, page_number=1, field="created_at", order="DESC"):
            return CustomComponentInstallationList(data=[], total=0, has_more=False)

        async def get_latest_installation_logs(self):
            raise Exception("API Error")

    fake_client = BaseFakeClient()
    fake_client.custom_components = lambda workspace: FakeCustomComponentsResource(fake_client)

    result = await get_latest_custom_component_installation_logs(fake_client, "test-workspace")

    assert result == "Failed to retrieve latest installation logs: API Error"
