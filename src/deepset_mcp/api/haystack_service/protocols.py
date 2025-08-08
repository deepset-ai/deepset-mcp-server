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

    async def run_component(
        self,
        component_type: str,
        init_params: dict[str, Any] | None = None,
        input_data: dict[str, Any] | None = None,
        input_types: dict[str, str] | None = None,
        workspace: str | None = None,
    ) -> dict[str, Any]:
        """Run a Haystack component with the given parameters.

        :param component_type: The type of component to run
            (e.g., "haystack.components.builders.prompt_builder.PromptBuilder")
        :param init_params: Initialization parameters for the component
        :param input_data: Input data for the component
        :param input_types: Optional type information for inputs (inferred if not provided)
        :param workspace: Optional workspace name to run the component in

        :returns: Dictionary containing the component's output sockets
        """
        ...
