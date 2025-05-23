from deepset_mcp.api.indexes.models import Index, IndexList


def index_to_llm_readable_string(index: Index) -> str:
    """Creates a string representation of an index that is readable by LLMs."""
    index_parts = [
        f"""<index name="{index.name}" id="{index.pipeline_index_id}">

### Basic Information

**Name:** {index.name}
**ID:** {index.pipeline_index_id}
**Description:** {index.description if index.description else "No description provided"}\n'
"""
    ]

    if index.config_yaml is not None:
        index_parts.append("\n### Index Configuration")
        index_parts.append(f"\n```yaml\n{index.config_yaml}\n```")

    index_parts.append(f'\n</index name="{index.name}" id="{index.pipeline_index_id}">')

    return "\n".join(index_parts)


def index_list_to_llm_readable_string(index_list: IndexList) -> str:
    """Creates a string representation of a list of indexes that is readable by LLMs."""
    if not index_list.data:
        return "No indexes found."

    index_strings = [index_to_llm_readable_string(index) for index in index_list.data]
    return "\n\n".join(index_strings)
