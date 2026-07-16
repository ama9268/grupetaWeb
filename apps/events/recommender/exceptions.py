class WindDataUnavailable(Exception):
    """La previsión de viento no está disponible para esta ruta/instante: fallo de red,
    timeout, fecha fuera del horizonte de previsión de Open-Meteo, o la ruta no tiene
    geometría/punto de inicio válidos."""


class LLMUnavailable(Exception):
    """El proveedor LLM configurado no ha podido generar una explicación: timeout, error
    de red, error de autenticación, o ROUTE_RECOMMENDER_LLM_PROVIDER=none."""
