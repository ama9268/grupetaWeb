"""Previsión de viento (Open-Meteo, gratuito, sin API key) y favorabilidad del viento.

Cualquier fallo (red, timeout, fecha fuera del horizonte de previsión, respuesta
inesperada) se traduce a `WindDataUnavailable` — nunca deja escapar una excepción de
terceros hacia el llamante (ver apps/events/CLAUDE.md, sección "Salidas").
"""
import math
from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone

import requests
from django.conf import settings
from django.utils import timezone as dj_timezone

from .exceptions import WindDataUnavailable


@dataclass
class WindSample:
    speed_kmh: float
    from_deg: float  # convención meteorológica: dirección DE LA QUE viene el viento


def fetch_wind_forecast(*, lat: float, lon: float, at: datetime) -> WindSample:
    """Previsión horaria de viento en `(lat, lon)` para el instante `at`. Todo el
    pipeline interno trabaja en UTC (independientemente de la zona horaria de `at`) para
    no arrastrar bugs de conversión/DST; la hora local solo se usa al pintar plantillas.
    """
    at_utc = dj_timezone.localtime(at, dt_timezone.utc)

    try:
        response = requests.get(
            settings.OPEN_METEO_BASE_URL,
            params={
                'latitude': lat,
                'longitude': lon,
                'hourly': 'windspeed_10m,winddirection_10m',
                'timezone': 'UTC',
                'start_date': at_utc.date().isoformat(),
                'end_date': at_utc.date().isoformat(),
            },
            timeout=settings.ROUTE_RECOMMENDER_HTTP_TIMEOUT_S,
        )
        response.raise_for_status()
        payload = response.json()
        hourly = payload['hourly']
        times = hourly['time']
        speeds = hourly['windspeed_10m']
        directions = hourly['winddirection_10m']
    except (requests.RequestException, KeyError, ValueError) as exc:
        raise WindDataUnavailable(f'No se pudo obtener la previsión de viento: {exc}') from exc

    target_hour = at_utc.strftime('%Y-%m-%dT%H:00')
    try:
        index = times.index(target_hour)
    except ValueError as exc:
        raise WindDataUnavailable(
            f'Open-Meteo no devolvió previsión para {target_hour} (¿fuera del horizonte de previsión?).'
        ) from exc

    return WindSample(speed_kmh=float(speeds[index]), from_deg=float(directions[index]))


def tailwind_kmh(return_bearing_deg: float, wind: WindSample) -> float:
    """Componente de viento a favor (positivo) o en contra (negativo) en el tramo de
    vuelta, en km/h equivalentes. `wind.from_deg` es de dónde SOPLA el viento (convención
    meteorológica); "hacia dónde sopla" es ese valor + 180°. Un único escalar, criterio
    de orden determinista para el ranking de candidatas."""
    blowing_towards_deg = (wind.from_deg + 180) % 360
    angle_diff = min(
        abs(blowing_towards_deg - return_bearing_deg),
        360 - abs(blowing_towards_deg - return_bearing_deg),
    )
    return wind.speed_kmh * math.cos(math.radians(angle_diff))
