from django.conf import settings


def get_llm_client():
    """Backend LLM activo según `settings.ROUTE_RECOMMENDER_LLM_PROVIDER`
    (`'anthropic' | 'ollama' | 'none'`). Import perezoso de cada backend para no exigir
    el SDK de Anthropic instalado si nunca se usa ese proveedor."""
    provider = settings.ROUTE_RECOMMENDER_LLM_PROVIDER
    if provider == 'anthropic':
        from .anthropic_client import AnthropicRouteLLM
        return AnthropicRouteLLM()
    if provider == 'ollama':
        from .ollama_client import OllamaRouteLLM
        return OllamaRouteLLM()
    from .null_client import NullRouteLLM
    return NullRouteLLM()
