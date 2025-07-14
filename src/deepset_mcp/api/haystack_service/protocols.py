# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any, Protocol


class HaystackServiceProtocol(Protocol):
    """Protocol defining the implementation for HaystackService."""

    async def get_component_schemas(self) -> dict[str, Any]:
        """Fetch the component schema from the API."""
        ...

    async def get_component_input_output(self, component_name: str) -> dict[str, Any]:
        """Fetch input and output schema for a component from the API."""
        ...
