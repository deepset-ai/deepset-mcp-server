# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any

import httpx

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.pipeline.models import DeepsetSearchResponse
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.config import DOCS_BASE_URL, DOCS_SEARCH_API_URL

DOC_SECTIONS: dict[str, str] = {
    "getting-started": "Quickstart guides, installation, and first steps with the Haystack Platform",
    "concepts": "Core concepts like pipelines, components, document stores, and embeddings",
    "how-to-guides": "Step-by-step guides for specific tasks",
    "tutorials": "End-to-end tutorials for building AI applications",
    "api": "REST API reference documentation",
    "learn": "In-depth articles about AI concepts and best practices",
}


def _absolute_docs_url(url: str) -> str:
    """Turn a docs-relative path into an absolute documentation URL."""
    if url.startswith("/"):
        return f"{DOCS_BASE_URL}{url}"
    return url


def format_docs_search_response(data: dict[str, Any]) -> str:
    """Format a docs-search chat or search response for an LLM.

    Matches the deepset documentation MCP server so agents see titles, URLs, and
    excerpts from the same pipeline that powers docs.cloud.deepset.ai.

    :param data: JSON body returned by the documentation search API.
    :returns: Formatted search results.
    """
    output_parts: list[str] = []
    results = data.get("results") or []

    if not results:
        return "No results found for your query."

    for result in results:
        query = result.get("query")
        if query:
            output_parts.append(f"# Search Results for: {query}\n")

        for answer in result.get("answers") or []:
            answer_text = answer.get("answer") or ""
            if not answer_text:
                continue

            output_parts.append("## Answer")
            answer_type = answer.get("type") or ""
            if answer_type:
                output_parts.append(f"*Type: {answer_type}*")
            output_parts.append(f"\n{answer_text}\n")

            context = answer.get("context") or ""
            if context and context != answer_text:
                output_parts.append(f"**Context:** {context}\n")

            meta = answer.get("meta") or {}
            title = meta.get("title") or meta.get("heading") or ""
            url = meta.get("url") or meta.get("slug") or ""
            if title:
                output_parts.append(f"**Source:** {title}")
            if url:
                output_parts.append(f"**URL:** {_absolute_docs_url(str(url))}")

            score = answer.get("score")
            if score is not None:
                output_parts.append(f"**Relevance Score:** {float(score):.2f}")

            output_parts.append("")

        documents = result.get("documents") or []
        if documents:
            output_parts.append("## Source Documents\n")
            for index, doc in enumerate(documents[:5], start=1):
                meta = doc.get("meta") or {}
                title = (
                    meta.get("heading")
                    or meta.get("parent_page")
                    or meta.get("title")
                    or meta.get("name")
                    or f"Document {index}"
                )
                url = meta.get("url") or meta.get("slug") or ""
                content = doc.get("content") or ""
                score = doc.get("score")

                output_parts.append(f"### {index}. {title}")
                if url:
                    output_parts.append(f"URL: {_absolute_docs_url(str(url))}")
                if score is not None:
                    output_parts.append(f"Score: {float(score):.2f}")
                if content:
                    display_content = content[:800] + "..." if len(content) > 800 else content
                    output_parts.append(f"\n{display_content}\n")
                output_parts.append("")

    return "\n".join(output_parts) if output_parts else "No results found for your query."


def doc_search_results_to_llm_readable_string(*, results: DeepsetSearchResponse) -> str:
    """Formats results of the doc search pipeline so that they can be read by an LLM.

    :param results: DeepsetSearchResponse object
    :return: Formatted results.
    """
    file_segmented_docs = []

    previous_source_id = None
    for doc in results.documents:
        if previous_source_id != doc.meta["source_id"]:
            file_segmented_docs.append([{"content": doc.content, "file_path": doc.meta.get("original_file_path", "")}])
            previous_source_id = doc.meta.get("source_id")
        else:
            file_segmented_docs[-1].append(
                {"content": doc.content, "file_path": doc.meta.get("original_file_path", "")}
            )

    files = []
    for file_docs in file_segmented_docs:
        start = file_docs[0]["file_path"]
        full_doc = " ".join([doc["content"] for doc in file_docs])
        files.append(start + "\n" + full_doc)

    return "\n----\n".join(files)


async def search_docs_via_docs_api(*, query: str, search_url: str = DOCS_SEARCH_API_URL) -> str:
    """Search the Haystack Enterprise Platform documentation via the public docs search API.

    This is the same backend used by the documentation MCP server at
    https://docs.cloud.deepset.ai/api/mcp.

    :param query: The search query to execute.
    :param search_url: Documentation search endpoint. Defaults to the public docs search API.
    :returns: Formatted search results or an error message.
    """
    if not query:
        return "Error: No query provided."

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(search_url, json={"query": query})
    except Exception as error:
        return f"Error: {error}"

    if response.status_code != 200:
        return f"Error: Search API returned status {response.status_code}"

    try:
        data = response.json()
    except Exception as error:
        return f"Error: {error}"

    if not isinstance(data, dict):
        return "Error: Search API returned an unexpected response."

    return format_docs_search_response(data)


async def search_docs(*, client: AsyncClientProtocol, workspace: str, pipeline_name: str, query: str) -> str:
    """Search deepset documentation using a dedicated docs pipeline.

    Uses the specified pipeline to perform a search with the given query against the deepset
    documentation. Before executing the search, checks if the pipeline is deployed (status = DEPLOYED).
    Returns search results in a human-readable format.

    :param client: The async client for API communication.
    :param workspace: The workspace name for the docs pipeline.
    :param pipeline_name: Name of the pipeline to use for doc search.
    :param query: The search query to execute.
    :returns: A string containing the formatted search results or error message.
    """
    try:
        search_response = await client.pipelines(workspace=workspace).search(pipeline_name=pipeline_name, query=query)

        return doc_search_results_to_llm_readable_string(results=search_response)

    except ResourceNotFoundError:
        return f"There is no documentation pipeline named '{pipeline_name}' in workspace '{workspace}'."
    except BadRequestError as e:
        return f"Failed to search documentation using pipeline '{pipeline_name}': {e}"
    except UnexpectedAPIError as e:
        return f"Failed to search documentation using pipeline '{pipeline_name}': {e}"
    except Exception as e:
        return f"An unexpected error occurred while searching documentation with pipeline '{pipeline_name}': {str(e)}"


async def list_doc_sections() -> str:
    """List the main sections of the deepset AI Platform documentation.

    Use this to understand what documentation is available and help users navigate
    to the right section.

    :returns: A list of documentation sections with descriptions and URLs.
    """
    output_parts = [
        "# Haystack Enterprise Platform Documentation Sections\n",
        f"Base URL: {DOCS_BASE_URL}\n",
    ]

    for section, description in DOC_SECTIONS.items():
        url = f"{DOCS_BASE_URL}/docs/{section}"
        title = section.replace("-", " ").title()
        output_parts.append(f"## {title}")
        output_parts.append(f"URL: {url}")
        output_parts.append(f"{description}\n")

    return "\n".join(output_parts)
