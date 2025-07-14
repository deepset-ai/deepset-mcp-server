# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.pipeline.models import DeepsetSearchResponse
from deepset_mcp.api.protocols import AsyncClientProtocol


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
