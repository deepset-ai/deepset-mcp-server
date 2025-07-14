# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from enum import StrEnum


class LogLevel(StrEnum):
    """Log level filter options for pipeline logs."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
