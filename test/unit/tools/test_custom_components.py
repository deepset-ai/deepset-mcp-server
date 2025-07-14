# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

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

    result = await list_custom_component_installations(client=client, workspace="test-workspace")

    assert isinstance(result, CustomComponentInstallationList)
    assert len(result.data) == 2
    assert result.total == 2
    assert result.has_more is False

    # Check first installation
    first_install = result.data[0]
    assert first_install.custom_component_id == "comp_123"
    assert first_install.status == "installed"
    assert first_install.version == "1.0.0"
    assert first_install.created_by_user_id == "user_123"
    assert len(first_install.logs) == 1
    assert first_install.logs[0]["level"] == "INFO"
    assert first_install.user_info is not None
    assert first_install.user_info.given_name == "John"
    assert first_install.user_info.family_name == "Doe"
    assert first_install.user_info.email == "john.doe@example.com"

    # Check second installation
    second_install = result.data[1]
    assert second_install.custom_component_id == "comp_456"
    assert second_install.status == "failed"
    assert second_install.version == "0.9.0"
    assert second_install.created_by_user_id == "user_456"
    assert len(second_install.logs) == 2
    assert second_install.user_info is not None
    assert second_install.user_info.given_name == "Jane"
    assert second_install.user_info.family_name == "Smith"
    assert second_install.user_info.email == "jane.smith@example.com"


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

    result = await list_custom_component_installations(client=client, workspace="test-workspace")

    assert isinstance(result, CustomComponentInstallationList)
    assert len(result.data) == 0
    assert result.total == 0
    assert result.has_more is False


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

    result = await list_custom_component_installations(client=client, workspace="test-workspace")

    assert isinstance(result, CustomComponentInstallationList)
    assert len(result.data) == 1
    assert result.data[0].created_by_user_id == "user_unknown"
    assert result.data[0].user_info is None  # User fetch failed, so user_info should be None


@pytest.mark.asyncio
async def test_list_custom_component_installations_api_error() -> None:
    """Test listing custom component installations when API fails."""
    custom_components_resource = FakeCustomComponentsResource(exception=Exception("API Error"))
    user_resource = FakeUserResource()
    client = FakeClient(
        custom_components_resource=custom_components_resource,
        user_resource=user_resource,
    )

    result = await list_custom_component_installations(client=client, workspace="test-workspace")

    assert result == "Failed to retrieve custom component installations: API Error"


@pytest.mark.asyncio
async def test_get_latest_custom_component_installation_logs() -> None:
    """Test getting latest custom component installation logs."""
    mock_logs = "Installation started\nInstalling dependencies\nInstallation complete"

    custom_components_resource = FakeCustomComponentsResource(latest_logs_response=mock_logs)
    client = FakeClient(custom_components_resource=custom_components_resource)

    result = await get_latest_custom_component_installation_logs(client=client, workspace="test-workspace")

    assert result == mock_logs


@pytest.mark.asyncio
async def test_get_latest_custom_component_installation_logs_empty() -> None:
    """Test getting latest custom component installation logs when none exist."""
    custom_components_resource = FakeCustomComponentsResource(latest_logs_response=None)
    client = FakeClient(custom_components_resource=custom_components_resource)

    result = await get_latest_custom_component_installation_logs(client=client, workspace="test-workspace")

    assert result == "No installation logs found."


@pytest.mark.asyncio
async def test_get_latest_custom_component_installation_logs_api_error() -> None:
    """Test getting latest custom component installation logs when API fails."""
    custom_components_resource = FakeCustomComponentsResource(
        exception=UnexpectedAPIError(status_code=500, message="API Error")
    )
    client = FakeClient(custom_components_resource=custom_components_resource)

    result = await get_latest_custom_component_installation_logs(client=client, workspace="test-workspace")
    assert result == "Failed to retrieve latest installation logs: API Error (Status Code: 500)"
