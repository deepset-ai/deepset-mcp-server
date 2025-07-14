# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any, Protocol

import numpy as np


class ModelProtocol(Protocol):
    """Protocol for static embedding models."""

    def encode(self, sentences: list[str] | str) -> np.ndarray[Any, Any]:
        """
        Encodes a single or multiple sentences.

        :param sentences: Single sentence or list of sentences to encode
        :returns: Numpy array of encoded sentences
        """
        ...
