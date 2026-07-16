"""Interfaz común de los backends LLM del agente de recomendación de ruta.

El LLM SOLO narra en castellano un ranking ya calculado (ver `recommender/service.py`) —
nunca reordena candidatas ni inventa cifras: los LLM no son fiables para aritmética ni
geometría, y aquí ya está resuelta en Python. Cualquier implementación debe lanzar
`LLMUnavailable` ante cualquier fallo (timeout, red, autenticación) para que el llamante
pueda degradar sin propagar un 500.
"""
from abc import ABC, abstractmethod

SYSTEM_PROMPT = (
    'Eres un asistente que ayuda a un club de ciclismo a elegir la ruta de una salida. '
    'Se te da un ranking de rutas candidatas YA CALCULADO (distancia, desnivel, y la '
    'favorabilidad del viento en el tramo de vuelta, en km/h equivalentes: positivo es '
    'viento a favor, negativo en contra). Redacta una explicación breve (2-4 frases) en '
    'castellano de por qué la primera candidata es la recomendada, y menciona alguna '
    'alternativa si el margen con la siguiente es pequeño. No inventes ni cambies '
    'ninguna cifra: limítate a explicar las que se te dan. Si no hay candidatas, dilo '
    'con claridad y no inventes una ruta.'
)


def format_result_for_prompt(result) -> str:
    """Convierte un `RecommendationResult` en texto plano para el prompt del LLM."""
    if not result.candidates:
        return 'No hay ninguna ruta candidata que encaje con los objetivos indicados.'

    lines = []
    if result.tolerance_widened:
        lines.append('(La tolerancia de km/desnivel se amplió porque no había candidatas exactas.)')
    for i, candidate in enumerate(result.candidates, start=1):
        wind_txt = (
            f'{candidate.tailwind_kmh:+.1f} km/h de viento en la vuelta'
            if candidate.wind_available else 'sin datos de viento disponibles'
        )
        loop_txt = ' (circuito)' if candidate.is_loop else ''
        lines.append(
            f'{i}. "{candidate.route.title}"{loop_txt}: {candidate.route.distance_km} km, '
            f'{candidate.route.elevation_gain_m if candidate.route.elevation_gain_m is not None else "?"} '
            f'm de desnivel, {wind_txt}.'
        )
    return '\n'.join(lines)


class RouteRecommenderLLM(ABC):
    @abstractmethod
    def explain(self, *, result) -> str:
        """`result`: `recommender.service.RecommendationResult`. Devuelve texto en
        castellano listo para mostrar. Debe lanzar `LLMUnavailable` en cualquier fallo."""
