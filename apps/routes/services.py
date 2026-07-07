"""Servicios reutilizables del módulo de rutas.

Centraliza la validación de ficheros GPX y la creación de rutas a partir de un
GPX para poder reutilizarlas tanto desde el módulo `routes` como desde `events`
(al subir un GPX nuevo mientras se crea/edita un evento).
"""
from django.core.exceptions import ValidationError

from .gpx_utils import parse_gpx
from .models import Route

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


def create_route_from_gpx(*, author, gpx_file, title, description=''):
    """Crea una Route a partir de un GPX y le extrae las estadísticas.

    Si el parseo del GPX falla, la ruta se crea igualmente sin estadísticas
    (mismo comportamiento tolerante que el flujo de creación de rutas).
    """
    route = Route(author=author, title=title, description=description, gpx_file=gpx_file)
    try:
        gpx_data = parse_gpx(gpx_file)
        route.distance_km = gpx_data['distance_km']
        route.elevation_gain_m = gpx_data['elevation_gain_m']
        route.elevation_loss_m = gpx_data['elevation_loss_m']
        route.max_elevation_m = gpx_data['max_elevation_m']
        route.min_elevation_m = gpx_data['min_elevation_m']
        route.track_geojson = gpx_data['track_points']
        route.elevation_profile = gpx_data['elevation_profile']
        parsed = True
    except Exception:
        parsed = False
    route.save()
    return route, parsed
