from deepset_mcp.api.pipeline.models import DeepsetPipeline, PipelineValidationResult
from deepset_mcp.api.pipeline_template.models import PipelineTemplate


def pipeline_template_to_llm_readable_string(template: PipelineTemplate, include_yaml: bool = False) -> str:
    """Creates a string representation of a pipeline template that is readable by LLMs."""
    template_parts = [
        f'''<pipeline_template name="{template.template_name}" id="{template.pipeline_template_id}">

### Basic Information

**Name:** {template.template_name}
**Author:** {template.author}
**Description:** {template.description}
'''
    ]

    if template.best_for:
        template_parts.append("\n### Best For\n" + "\n".join(f"- {use}" for use in template.best_for))

    if template.potential_applications:
        template_parts.append(
            "\n### Potential Applications\n" + "\n".join(f"- {app}" for app in template.potential_applications)
        )

    if template.tags:
        template_parts.append("\n### Tags\n" + "\n".join(f"- {tag.name}" for tag in template.tags))

    if template.yaml_config is not None and include_yaml:
        template_parts.append("\n### Template Configuration")
        template_parts.append(f"\n```yaml\n{template.yaml_config}\n```")

    template_parts.append(
        f'\n</pipeline_template name="{template.template_name}" id="{template.pipeline_template_id}">'
    )

    return "\n".join(template_parts)


def pipeline_to_llm_readable_string(pipeline: DeepsetPipeline) -> str:
    """Creates a string representation of a pipeline that is readable by LLMs."""
    pipeline_parts = [
        f"""<pipeline name="{pipeline.name}" id="{pipeline.id}">

### Basic Information

**Name:** {pipeline.name}
**ID:** {pipeline.id}
**Status:** {pipeline.status}
**Service Level:** {pipeline.service_level}

**Created At:** {pipeline.created_at.strftime("%B %d, %Y %I:%M %p")}"""
    ]

    if pipeline.created_by.given_name is not None:
        user_info = f"**Created By:** {pipeline.created_by.given_name} {pipeline.created_by.family_name}"
        pipeline_parts.append(user_info)

    if pipeline.last_updated_at is not None and pipeline.last_updated_at != pipeline.created_at:
        pipeline_parts.append(f"**Last Updated:** {pipeline.last_updated_at.strftime('%B %d, %Y %I:%M %p')}")

    if pipeline.last_updated_by is not None:
        updater_info = (
            f"**Last Updated By:** {pipeline.last_updated_by.given_name} {pipeline.last_updated_by.family_name}"
        )
        pipeline_parts.append(updater_info)

    if pipeline.yaml_config is not None:
        pipeline_parts.append("\n\n### Pipeline Configuration")
        pipeline_parts.append(f"\n```yaml\n{pipeline.yaml_config}\n```")

    pipeline_parts.append(f'\n</pipeline name="{pipeline.name}" id="{pipeline.id}">')

    return "\n".join(pipeline_parts)


def validation_result_to_llm_readable_string(validation_result: PipelineValidationResult) -> str:
    """Creates a string representation of a pipeline validation result that is readable by LLMs."""
    result_parts = [f"The provided pipeline configuration is {'valid' if validation_result.valid else 'invalid'}."]

    if not validation_result.valid and validation_result.errors:
        result_parts.append("\n**Validation Errors**\n")

        for i, error in enumerate(validation_result.errors, 1):
            result_parts.append(f"Error {i}\n- Code: {error.code}\n- Message: {error.message}\n")

    return "\n".join(result_parts)
