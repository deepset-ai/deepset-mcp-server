# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Tools for interacting with models."""

import asyncio
import time
from typing import Any

from pydantic import BaseModel

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.model.models import Model, ModelCategory, ModelList, ModelProvider
from deepset_mcp.api.protocols import AsyncClientProtocol

MAX_COMPARED_MODELS = 5
MODEL_RUN_TIMEOUT_SECONDS = 120.0
DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant. Answer concisely."


class ModelRun(BaseModel):
    """One model's answer to the prompt, or why it has none."""

    model: str
    "The model as it was asked for."
    reply: str | None = None
    total_tokens: int | None = None
    latency_ms: int | None = None
    error: str | None = None


class ModelComparison(BaseModel):
    """The models' answers to the same prompt, in the order the models were given."""

    runs: list[ModelRun]


async def get_models(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    limit: int = 100,
    page_number: int = 1,
    connected: bool | None = None,
    provider: ModelProvider | str | None = None,
    model: str | None = None,
    include_price: bool = False,
    category: ModelCategory | None = None,
) -> ModelList | str:
    """Lists the models including their configuration options available for use in a workspace's pipelines and indexes.

    This includes predefined models offered by deepset as well as custom models configured
    at the workspace or organization level. Use this tool to discover which model names and
    providers can be used, which configuration options are available, and which default
    configuration is offered when configuring chat generators.

    Without `category`, only LLMs are listed. To find the embedders and rerankers deepset hosts, pass
    `category="EMBEDDER"` or `category="RANKER"`. Each of these models carries `components`: the ready-to-use
    pipeline components by role (`document_embedder` for the indexing pipeline, `text_embedder` and `ranker` for
    the query pipeline), plus `details` to compare them on (embedding dimension, max input tokens, languages,
    MTEB retrieval score). Use the same embedder in the indexing and the query pipeline: switching an embedder
    means re-indexing the documents. Don't pick a model with `stage` LEGACY for a new pipeline; EXPERIMENTAL
    models are still being tried out.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param limit: Maximum number of models to return per page.
    :param page_number: The page to fetch, starting at 1.
    :param connected: If set, only return models for which the workspace does (True) or
        does not (False) have a working integration configured.
    :param provider: If set, only return models from this provider. Accepts a well-known
        `ModelProvider` value (e.g. 'openai', 'anthropic', 'gemini', 'aws-bedrock') or any other
        provider name as a plain string. Case-insensitive, exact match.
    :param model: If set, only return models whose configured model name contains this value
        (e.g. 'gpt-4o'). Case-insensitive, substring match.
    :param include_price: If True, each model also carries its effective `price` in USD per 1,000 tokens
        (input, output and cache prices), with the workspace's and organization's custom prices applied.
        Requires read access to costs. Models without a known price have no `price`, e.g. Azure models that
        are only identified by their deployment name. Defaults to False.
    :param category: The kind of model to list: 'LLM', 'EMBEDDER' or 'RANKER'. Defaults to LLMs only.
    :returns: A page of models including their configuration options or an error message.
    """
    try:
        return await client.models(workspace=workspace).list(
            limit=limit,
            page_number=page_number,
            connected=connected,
            provider=provider,
            model=model,
            include_price=include_price,
            category=category,
        )
    except ResourceNotFoundError:
        return f"There is no workspace named '{workspace}'. Did you mean to configure it?"
    except UnexpectedAPIError as e:
        if include_price and e.status_code == 403:
            return (
                "Prices need read access to costs in this workspace, which the API key does not have. "
                "Call get_models without include_price to list the models."
            )
        return f"Failed to list models: {e}"
    except BadRequestError as e:
        return f"Failed to list models: {e}"


def _reply_text(output: dict[str, Any]) -> str:
    """Chat generators answer with `replies[0].content = [{text}]` (or `.text`) across providers."""
    replies = output.get("replies")
    if not isinstance(replies, list) or not replies or not isinstance(replies[0], dict):
        return ""
    reply = replies[0]
    if isinstance(reply.get("text"), str):
        return str(reply["text"])
    content = reply.get("content")
    if not isinstance(content, list):
        return ""
    return "".join(part if isinstance(part, str) else str(part.get("text") or "") for part in content)


def _total_tokens(output: dict[str, Any]) -> int | None:
    """OpenAI and Bedrock report `total_tokens`, Gemini `total_token_count`."""
    replies = output.get("replies")
    if not isinstance(replies, list) or not replies or not isinstance(replies[0], dict):
        return None
    usage = (replies[0].get("meta") or {}).get("usage") or {}
    total = usage.get("total_tokens", usage.get("total_token_count"))
    return total if isinstance(total, int) else None


async def _find_model(client: AsyncClientProtocol, workspace: str, name: str) -> Model | str:
    found = await client.models(workspace=workspace).list(model=name)
    exact = [m for m in found.data if name.lower() in (m.name.lower(), (m.model or "").lower())]
    if not exact:
        return f"No LLM named '{name}' in this workspace. Use get_models to find the model names."
    if exact[0].connected is False:
        return f"'{name}' is not connected in this workspace: it needs an integration with {exact[0].provider}."
    return exact[0]


async def _run_model(
    client: AsyncClientProtocol,
    workspace: str,
    name: str,
    messages: list[dict[str, str]],
    generation_kwargs: dict[str, Any] | None,
) -> ModelRun:
    try:
        found = await _find_model(client, workspace, name)
        if isinstance(found, str):
            return ModelRun(model=name, error=found)
        config = found.chat_generator_config
        input_data: dict[str, Any] = {"messages": messages}
        if generation_kwargs:
            input_data["generation_kwargs"] = generation_kwargs
        started = time.perf_counter()
        output = await asyncio.wait_for(
            client.haystack_service().run_component(
                component_type=config.get("type", ""),
                init_params=config.get("init_parameters") or {},
                input_data=input_data,
                workspace=workspace,
            ),
            timeout=MODEL_RUN_TIMEOUT_SECONDS,
        )
        return ModelRun(
            model=name,
            reply=_reply_text(output),
            total_tokens=_total_tokens(output),
            latency_ms=round((time.perf_counter() - started) * 1000),
        )
    except TimeoutError:
        return ModelRun(model=name, error=f"No answer within {MODEL_RUN_TIMEOUT_SECONDS:.0f} seconds.")
    except Exception as e:
        return ModelRun(model=name, error=f"Failed to run the model: {e}")


async def compare_models(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    models: list[str],
    prompt: str,
    system_prompt: str | None = None,
    generation_kwargs: dict[str, Any] | None = None,
) -> ModelComparison | str:
    """Sends the same prompt to several LLMs and returns each one's answer, token count and latency.

    Use it to choose an LLM for a pipeline: find the candidates with get_models (pass `connected=True`, and
    `include_price=True` to weigh the answers against the price), then compare 2 to 5 of them on prompts typical of
    the user's use case. Each call runs every model once on the workspace's integrations, so it costs tokens with
    each provider: don't repeat it without need. A model's run fails on its own without affecting the others.
    Embedders and rerankers can't be compared this way; compare them on the `details` get_models returns.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param models: The LLMs to compare, by their `name` or `model` as get_models returns them, e.g. 'gpt-4o'.
        At most 5.
    :param prompt: The user message every model answers.
    :param system_prompt: The system message. Defaults to a short "helpful assistant" prompt.
    :param generation_kwargs: Generation parameters for every model, e.g. {"temperature": 0, "max_tokens": 512}.
        Each provider accepts its own keys; get_models lists them per model under `generation_kwargs`.
    :returns: Each model's answer, total tokens and latency in milliseconds, or the error it failed with.
    """
    if not models:
        return "Pass at least one model to compare."
    if len(models) > MAX_COMPARED_MODELS:
        return f"Compare at most {MAX_COMPARED_MODELS} models at once; {len(models)} were given."

    messages = [
        {"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    runs = await asyncio.gather(
        *(_run_model(client, workspace, name, messages, generation_kwargs) for name in dict.fromkeys(models))
    )
    return ModelComparison(runs=list(runs))
