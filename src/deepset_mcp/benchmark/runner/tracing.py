from haystack.tracing.tracer import enable_tracing as haystack_enable_tracing, tracer
from haystack_integrations.tracing.langfuse import LangfuseTracer
from langfuse import Langfuse


def enable_tracing(
    secret_key: str,
    public_key: str,
    name: str,
) -> None:
    """Enables tracing with langfuse."""
    resolved_langfuse_client_kwargs = {
        "secret_key": secret_key,
        "public_key": public_key,
    }
    tracer.is_content_tracing_enabled = True
    langfuse_tracer = LangfuseTracer(
        tracer=Langfuse(**resolved_langfuse_client_kwargs),
        name=name,
    )
    haystack_enable_tracing(langfuse_tracer)
