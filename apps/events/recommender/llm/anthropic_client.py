from django.conf import settings

from ..exceptions import LLMUnavailable
from .base import SYSTEM_PROMPT, RouteRecommenderLLM, format_result_for_prompt


class AnthropicRouteLLM(RouteRecommenderLLM):
    def explain(self, *, result) -> str:
        import anthropic

        try:
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=settings.LLM_TIMEOUT_S)
            response = client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=400,
                system=SYSTEM_PROMPT,
                messages=[{'role': 'user', 'content': format_result_for_prompt(result)}],
            )
        except anthropic.AnthropicError as exc:
            raise LLMUnavailable(str(exc)) from exc

        text = ''.join(block.text for block in response.content if block.type == 'text').strip()
        if not text:
            raise LLMUnavailable('Respuesta vacía del proveedor Anthropic.')
        return text
