"""Detección (no bloqueante) de rutas posiblemente duplicadas dentro de una grupeta.

Una misma ruta física puede existir, a propósito, una vez por grupeta (no hay
deduplicación entre grupetas): la comprobación siempre va acotada por `group`.
"""
from django.contrib.gis.measure import D

from .models import Route

DEDUP_RADIUS_M = 500
DISTANCE_TOLERANCE = 0.02   # ±2%
ELEVATION_TOLERANCE = 0.05  # ±5%


def find_possible_duplicate(*, group, start_point, distance_km, elevation_gain_m=None, exclude_pk=None):
    """Busca una ruta ya existente en `group` que parezca la misma.

    Compara el punto de inicio real (radio `DEDUP_RADIUS_M`) y la distancia total
    (tolerancia `DISTANCE_TOLERANCE`); si hay desnivel disponible, también lo
    compara (tolerancia `ELEVATION_TOLERANCE`). Devuelve la primera coincidencia o
    `None` — es un aviso informativo, nunca bloquea la creación de la ruta.
    """
    if not start_point or not distance_km:
        return None

    qs = Route.objects.filter(
        group=group,
        start_point__dwithin=(start_point, D(m=DEDUP_RADIUS_M)),
        distance_km__range=(
            distance_km * (1 - DISTANCE_TOLERANCE),
            distance_km * (1 + DISTANCE_TOLERANCE),
        ),
    )
    if elevation_gain_m:
        qs = qs.filter(elevation_gain_m__range=(
            elevation_gain_m * (1 - ELEVATION_TOLERANCE),
            elevation_gain_m * (1 + ELEVATION_TOLERANCE),
        ))
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    return qs.first()
