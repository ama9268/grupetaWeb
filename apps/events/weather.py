"""Meteorología general (Open-Meteo, gratuito, sin API key) para la ficha de
Eventos/Salidas: resumen puntual (temperatura, cielo, lluvia, viento) y rejilla de
viento para la animación en el mapa (`routes/partials/route_map.html`).

Mismo criterio que `apps/events/recommender/wind.py`: cualquier fallo (red, timeout,
fecha fuera del horizonte de previsión de Open-Meteo, ~16 días) se traduce a
`WeatherDataUnavailable` — nunca deja escapar una excepción de terceros hacia la vista,
que la degrada a un mensaje visible en vez de un 500 (ver apps/events/CLAUDE.md).

Separado deliberadamente de `recommender/wind.py`: ese módulo solo necesita
velocidad+dirección para el ranking del agente de recomendación (Salidas); este
módulo sirve el resumen visible en la ficha de CUALQUIER evento/salida con ruta
asociada, con más variables (temperatura, cielo, lluvia) y, además, la rejilla de
puntos para la animación de viento — dos consumidores con necesidades distintas.
"""
import math
from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone as dj_timezone


class WeatherDataUnavailable(Exception):
    """La previsión meteorológica no está disponible: fallo de red, timeout, fecha
    fuera del horizonte de previsión de Open-Meteo, o coordenadas inválidas."""


# Códigos WMO de Open-Meteo (`weathercode`) -> descripción corta en castellano.
# https://open-meteo.com/en/docs (tabla "WMO Weather interpretation codes").
_SKY_DESCRIPTIONS = {
    0: 'Despejado', 1: 'Poco nuboso', 2: 'Parcialmente nuboso', 3: 'Cubierto',
    45: 'Niebla', 48: 'Niebla engelante',
    51: 'Llovizna débil', 53: 'Llovizna', 55: 'Llovizna intensa',
    56: 'Llovizna helada', 57: 'Llovizna helada intensa',
    61: 'Lluvia débil', 63: 'Lluvia', 65: 'Lluvia intensa',
    66: 'Lluvia helada', 67: 'Lluvia helada intensa',
    71: 'Nieve débil', 73: 'Nieve', 75: 'Nieve intensa', 77: 'Granizo fino',
    80: 'Chubascos débiles', 81: 'Chubascos', 82: 'Chubascos intensos',
    85: 'Chubascos de nieve débiles', 86: 'Chubascos de nieve intensos',
    95: 'Tormenta', 96: 'Tormenta con granizo débil', 99: 'Tormenta con granizo fuerte',
}

# Mismos códigos WMO, agrupados en un puñado de iconos (ver
# templates/events/partials/weather_icon.html): no hay un icono por cada matiz de
# intensidad, solo por familia de fenómeno.
_SKY_ICONS = {
    0: 'sun', 1: 'sun',
    2: 'cloud', 3: 'cloud', 45: 'cloud', 48: 'cloud',
    51: 'rain', 53: 'rain', 55: 'rain', 56: 'rain', 57: 'rain',
    61: 'rain', 63: 'rain', 65: 'rain', 66: 'rain', 67: 'rain',
    80: 'rain', 81: 'rain', 82: 'rain',
    71: 'snow', 73: 'snow', 75: 'snow', 77: 'snow', 85: 'snow', 86: 'snow',
    95: 'storm', 96: 'storm', 99: 'storm',
}

_CACHE_TTL_S = 3600
# Puntos por lado de la rejilla de viento (resolution^2 puntos totales pedidos a
# Open-Meteo en una única llamada). 10x10=100 es deliberadamente menor que lo que usan
# otros proyectos hermanos (20x20=400): suficiente resolución para el área de una ruta
# de club, con una URL y un tiempo de respuesta contenidos.
_WIND_GRID_RESOLUTION = 10


def _sky_description(weathercode) -> str:
    try:
        return _SKY_DESCRIPTIONS.get(int(weathercode), 'Sin datos')
    except (TypeError, ValueError):
        return 'Sin datos'


def _sky_icon(weathercode) -> str:
    try:
        return _SKY_ICONS.get(int(weathercode), 'cloud')
    except (TypeError, ValueError):
        return 'cloud'


@dataclass
class WeatherSample:
    temperature_c: float
    sky_description: str
    sky_icon: str  # clave para templates/events/partials/weather_icon.html
    precipitation_probability_pct: float
    wind_speed_kmh: float
    wind_from_deg: float  # convención meteorológica: dirección DE LA QUE viene el viento


def fetch_weather_forecast(*, lat: float, lon: float, at: datetime) -> WeatherSample:
    """Previsión horaria (temperatura, cielo, lluvia, viento) en `(lat, lon)` para el
    instante `at`. Todo el pipeline interno trabaja en UTC, igual que
    `recommender.wind.fetch_wind_forecast` — la hora local solo se usa al pintar
    plantillas.
    """
    at_utc = dj_timezone.localtime(at, dt_timezone.utc)
    lat_r, lon_r = round(float(lat), 4), round(float(lon), 4)
    date_str = at_utc.date().isoformat()
    cache_key = f'events_weather_{lat_r}_{lon_r}_{date_str}_{at_utc.hour}'

    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        response = requests.get(
            settings.OPEN_METEO_BASE_URL,
            params={
                'latitude': lat, 'longitude': lon,
                'hourly': 'temperature_2m,precipitation_probability,weathercode,windspeed_10m,winddirection_10m',
                'timezone': 'UTC',
                'start_date': date_str, 'end_date': date_str,
            },
            timeout=settings.ROUTE_RECOMMENDER_HTTP_TIMEOUT_S,
        )
        response.raise_for_status()
        hourly = response.json()['hourly']
        times = hourly['time']
    except (requests.RequestException, KeyError, ValueError) as exc:
        raise WeatherDataUnavailable(f'No se pudo obtener la previsión meteorológica: {exc}') from exc

    target_hour = at_utc.strftime('%Y-%m-%dT%H:00')
    try:
        idx = times.index(target_hour)
        sample = WeatherSample(
            temperature_c=float(hourly['temperature_2m'][idx]),
            sky_description=_sky_description(hourly['weathercode'][idx]),
            sky_icon=_sky_icon(hourly['weathercode'][idx]),
            precipitation_probability_pct=float(hourly['precipitation_probability'][idx]),
            wind_speed_kmh=float(hourly['windspeed_10m'][idx]),
            wind_from_deg=float(hourly['winddirection_10m'][idx]),
        )
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise WeatherDataUnavailable(
            f'Open-Meteo no devolvió previsión para {target_hour} (¿fuera del horizonte de previsión?).'
        ) from exc

    cache.set(cache_key, sample, _CACHE_TTL_S)
    return sample


def fetch_wind_grid(*, min_lat: float, min_lon: float, max_lat: float, max_lon: float, at: datetime) -> list:
    """Rejilla de viento (componentes U/V) para una bounding box, en el formato que
    espera `leaflet-velocity` (lista de dos "mensajes" tipo GRIB, uno por componente).
    """
    at_utc = dj_timezone.localtime(at, dt_timezone.utc)
    lat1, lat2 = max(min_lat, max_lat), min(min_lat, max_lat)
    lon1, lon2 = min(min_lon, max_lon), max(min_lon, max_lon)
    nx = ny = _WIND_GRID_RESOLUTION

    date_str = at_utc.date().isoformat()
    cache_key = (
        f'events_windgrid_{lat1:.3f}_{lon1:.3f}_{lat2:.3f}_{lon2:.3f}_{date_str}_{at_utc.hour}'
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    d_lat = (lat1 - lat2) / (ny - 1) if ny > 1 else 0
    d_lon = (lon2 - lon1) / (nx - 1) if nx > 1 else 0
    lats, lons = [], []
    for i in range(ny):
        curr_lat = lat1 - i * d_lat
        for j in range(nx):
            lats.append(round(curr_lat, 4))
            lons.append(round(lon1 + j * d_lon, 4))

    try:
        response = requests.get(
            settings.OPEN_METEO_BASE_URL,
            params={
                'latitude': ','.join(map(str, lats)),
                'longitude': ','.join(map(str, lons)),
                'hourly': 'windspeed_10m,winddirection_10m',
                'timezone': 'UTC',
                'start_date': date_str, 'end_date': date_str,
            },
            timeout=settings.ROUTE_RECOMMENDER_HTTP_TIMEOUT_S * 3,
        )
        response.raise_for_status()
        results = response.json()
        if not isinstance(results, list):
            results = [results]
    except (requests.RequestException, ValueError) as exc:
        raise WeatherDataUnavailable(f'No se pudo obtener la rejilla de viento: {exc}') from exc

    target_hour = at_utc.strftime('%Y-%m-%dT%H:00')
    u_comp, v_comp = [], []
    for point in results:
        hourly = point.get('hourly', {}) if isinstance(point, dict) else {}
        times = hourly.get('time', [])
        try:
            idx = times.index(target_hour)
            speed = float(hourly['windspeed_10m'][idx])
            direction = float(hourly['winddirection_10m'][idx])
        except (ValueError, KeyError, IndexError, TypeError):
            # Punto de la rejilla sin dato horario (borde del horizonte de previsión):
            # se rellena en calma para no romper la forma fija nx*ny que espera
            # leaflet-velocity, en vez de descartar toda la rejilla por un punto suelto.
            speed = direction = 0.0
        # Convención GRIB: U=+Este, V=+Norte. wind_from_deg es de dónde SOPLA el viento
        # (convención meteorológica); "hacia dónde sopla" es ese valor + 180°.
        rad = math.radians(direction)
        u_comp.append(-speed * math.sin(rad))
        v_comp.append(-speed * math.cos(rad))

    if len(u_comp) != nx * ny:
        raise WeatherDataUnavailable('Open-Meteo no devolvió la rejilla de viento completa.')

    header_common = {
        'dx': d_lon, 'dy': d_lat, 'nx': nx, 'ny': ny,
        'lo1': lon1, 'la1': lat1, 'lo2': lon2, 'la2': lat2,
        'refTime': f'{date_str}T{at_utc.hour:02d}:00:00Z',
    }
    grid = [
        {'header': {**header_common, 'parameterCategory': 2, 'parameterNumber': 2}, 'data': u_comp},
        {'header': {**header_common, 'parameterCategory': 2, 'parameterNumber': 3}, 'data': v_comp},
    ]
    cache.set(cache_key, grid, _CACHE_TTL_S)
    return grid
