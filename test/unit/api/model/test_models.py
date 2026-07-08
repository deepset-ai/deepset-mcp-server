# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for model models."""

import uuid

from deepset_mcp.api.model.models import Model

MODEL_ID = uuid.uuid4()


def _make_model(**overrides: object) -> Model:
    defaults: dict[str, object] = {
        "model_id": MODEL_ID,
        "name": "gpt-4o",
        "provider": "openai",
        "chat_generator_config": {"type": "OpenAIChatGenerator", "init_parameters": {"model": "gpt-4o"}},
        "generation_kwargs": {},
    }
    defaults.update(overrides)
    return Model(**defaults)  # type: ignore[arg-type]


class TestModelInference:
    def test_model_inferred_from_chat_generator_config(self) -> None:
        model = _make_model()
        assert model.model == "gpt-4o"

    def test_explicit_model_wins_over_inferred_value(self) -> None:
        model = _make_model(model="explicit-model")
        assert model.model == "explicit-model"

    def test_model_is_none_when_init_parameters_missing(self) -> None:
        model = _make_model(chat_generator_config={"type": "OpenAIChatGenerator"})
        assert model.model is None

    def test_model_is_none_when_init_parameters_has_no_model_key(self) -> None:
        model = _make_model(
            chat_generator_config={"type": "OpenAIChatGenerator", "init_parameters": {"temperature": 0.5}}
        )
        assert model.model is None

    def test_model_is_none_when_model_value_is_not_a_string(self) -> None:
        model = _make_model(chat_generator_config={"type": "OpenAIChatGenerator", "init_parameters": {"model": 123}})
        assert model.model is None
