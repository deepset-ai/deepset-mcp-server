# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from functools import lru_cache

from model2vec import StaticModel


@lru_cache(maxsize=1)
def get_initialized_model() -> StaticModel:
    """Gets the initialized embedding model.

    The model is cached to avoid reloading.
    """
    return StaticModel.from_pretrained("minishlab/potion-base-2M")
