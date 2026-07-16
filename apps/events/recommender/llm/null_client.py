from ..exceptions import LLMUnavailable
from .base import RouteRecommenderLLM


class NullRouteLLM(RouteRecommenderLLM):
    """Backend por defecto (`ROUTE_RECOMMENDER_LLM_PROVIDER=none`): no hace ninguna
    llamada de red, para que el repo arranque limpio sin ninguna clave configurada. El
    botón "Explicar con IA" se oculta en la UI cuando este es el backend activo (ver
    `templates/events/partials/route_recommendation_results.html`)."""

    def explain(self, *, result) -> str:
        raise LLMUnavailable('No hay ningún proveedor LLM configurado (ROUTE_RECOMMENDER_LLM_PROVIDER=none).')
