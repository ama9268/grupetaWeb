import requests
from django.conf import settings

from ..exceptions import LLMUnavailable
from .base import SYSTEM_PROMPT, RouteRecommenderLLM, format_result_for_prompt


class OllamaRouteLLM(RouteRecommenderLLM):
    """Backend local: HTTP directo contra la API de chat de Ollama, sin SDK."""

    def explain(self, *, result) -> str:
        try:
            response = requests.post(
                f'{settings.OLLAMA_BASE_URL}/api/chat',
                json={
                    'model': settings.OLLAMA_MODEL,
                    'messages': [
                        {'role': 'system', 'content': SYSTEM_PROMPT},
                        {'role': 'user', 'content': format_result_for_prompt(result)},
                    ],
                    'stream': False,
                },
                timeout=settings.LLM_TIMEOUT_S,
            )
            response.raise_for_status()
            text = response.json()['message']['content'].strip()
        except (requests.RequestException, KeyError, ValueError) as exc:
            raise LLMUnavailable(str(exc)) from exc

        if not text:
            raise LLMUnavailable('Respuesta vacía del proveedor Ollama.')
        return text
