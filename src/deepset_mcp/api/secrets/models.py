# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel


class Secret(BaseModel):
    """Model representing a secret in deepset."""

    name: str
    secret_id: str
