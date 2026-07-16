"""Servicios reutilizables del módulo de rutas.

Centraliza la validación de ficheros GPX y la creación de rutas a partir de un
GPX (subida directa o actividad de Strava) para poder reutilizarlas tanto desde
el módulo `routes` como desde `events` (al subir un GPX nuevo mientras se
crea/edita un evento).
"""
from django.contrib.gis.geos import LineString, Point
from django.core.exceptions import ValidationError
from django.utils.html import format_html

from .dedup import find_possible_duplicate
from .gpx_utils import extract_gpx_stats, parse_gpx
from .models import Route


def duplicate_warning_message(duplicate):
    """Mensaje (HTML seguro) para avisar de una posible ruta duplicada.

    Reutilizado por `apps.routes.views` y `apps.events.views` — el aviso es
    siempre no bloqueante (ver apps/routes/dedup.py).
    """
    return format_html(
        'Puede que esta ruta ya existiera en la grupeta: <a href="{}">{}</a>. Se ha guardado igualmente.',
        duplicate.get_absolute_url(), duplicate.title,
    )

MAX_GPX_SIZE = 10 * 1024 * 1024  # 10 MB
GPX_HEADER_BYTES = 512


def _is_valid_gpx(file) -> bool:
    """Comprueba los primeros bytes para confirmar que es XML con un elemento <gpx."""
    header = file.read(GPX_HEADER_BYTES)
    file.seek(0)
    # Ignorar el BOM UTF-8 si está presente.
    if header.startswith(b'\xef\xbb\xbf'):
        header = header[3:]
    try:
        text = header.decode('utf-8', errors='ignore').strip().lower()
    except Exception:
        return False
    return ('<gpx' in text) or (text.startswith('<?xml') and 'gpx' in text)


def validate_gpx_upload(file):
    """Valida tamaño y cabecera de un GPX subido. Devuelve el fichero o lanza ValidationError."""
    if file.size > MAX_GPX_SIZE:
        raise ValidationError('El archivo GPX no puede superar 10 MB.')
    if not _is_valid_gpx(file):
        raise ValidationError(
            'El archivo no parece un GPX válido. Comprueba que contenga datos de ruta en formato XML/GPX.'
        )
    return file


def _apply_gpx_stats(route, gpx_data):
    route.distance_km = gpx_data['distance_km']
    route.elevation_gain_m = gpx_data['elevation_gain_m']
    route.elevation_loss_m = gpx_data['elevation_loss_m']
    route.max_elevation_m = gpx_data['max_elevation_m']
    route.min_elevation_m = gpx_data['min_elevation_m']
    route.track_geojson = gpx_data['track_points']
    route.elevation_profile = gpx_data['elevation_profile']

    points = gpx_data['track_points']
    if len(points) >= 2:
        route.track_geom = LineString([(lon, lat) for lat, lon in points], srid=4326)
    if points:
        route.start_point = Point(points[0][1], points[0][0], srid=4326)


def create_route_from_gpx(*, group, author, gpx_file, title, description=''):
    """Crea una Route a partir de un GPX y le extrae las estadísticas.

    Si el parseo del GPX falla, la ruta se crea igualmente sin estadísticas
    (mismo comportamiento tolerante que antes). Devuelve `(route, parsed,
    possible_duplicate)`: `possible_duplicate` (apps/routes/dedup.py) es solo un
    aviso informativo — nunca impide crear la ruta.
    """
    route = Route(group=group, author=author, title=title, description=description, gpx_file=gpx_file)
    try:
        _apply_gpx_stats(route, parse_gpx(gpx_file))
        parsed = True
    except Exception:
        parsed = False

    duplicate = None
    if parsed:
        duplicate = find_possible_duplicate(
            group=group, start_point=route.start_point,
            distance_km=route.distance_km, elevation_gain_m=route.elevation_gain_m,
        )
    route.save()
    return route, parsed, duplicate


def create_route_from_strava_gpx(*, group, author, title, description, gpx, strava_activity_id):
    """Crea una Route a partir de una actividad de Strava ya convertida a un
    objeto `gpxpy.gpx.GPX` (`apps.routes.strava.build_gpx_from_streams`).

    Misma extracción de estadísticas y mismo aviso de duplicado (no bloqueante)
    que `create_route_from_gpx` — una única lógica de creación de rutas,
    independiente del origen del track.
    """
    route = Route(
        group=group, author=author, title=title, description=description,
        strava_activity_id=strava_activity_id,
    )
    _apply_gpx_stats(route, extract_gpx_stats(gpx))
    duplicate = find_possible_duplicate(
        group=group, start_point=route.start_point,
        distance_km=route.distance_km, elevation_gain_m=route.elevation_gain_m,
    )
    route.save()
    return route, duplicate
