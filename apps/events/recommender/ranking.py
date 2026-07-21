"""Filtrado determinista de rutas candidatas para una Salida, por grupeta y por
cercanía a los objetivos de distancia/desnivel. No reutiliza las tolerancias de
`apps/routes/dedup.py` (sirven a un propósito distinto — detección de duplicados, mucho
más estrechas — acoplarlas sería frágil).
"""
from django.conf import settings

from apps.routes.models import Route

MAX_TOLERANCE = 0.5  # tope del ensanchado progresivo: ±50%


def select_candidates(*, group, target_distance_km=None, target_elevation_gain_m=None):
    """Rutas de `group` con geometría utilizable, dentro de la tolerancia de los
    objetivos dados (un objetivo ausente no filtra). Si ninguna encaja, ensancha la
    tolerancia progresivamente (x2, x3, tope `MAX_TOLERANCE`) antes de rendirse.
    Devuelve `(queryset, tolerance_widened)`.
    """
    base_qs = Route.objects.filter(
        group=group, track_geojson__isnull=False, distance_km__isnull=False,
        recommendable_for_salidas=True, is_archived=False,
    )

    if not target_distance_km and not target_elevation_gain_m:
        return base_qs, False

    for multiplier in (1, 2, 3):
        qs = base_qs
        if target_distance_km:
            tolerance = min(settings.ROUTE_RECOMMENDER_DISTANCE_TOLERANCE * multiplier, MAX_TOLERANCE)
            target = float(target_distance_km)
            qs = qs.filter(distance_km__gte=target * (1 - tolerance), distance_km__lte=target * (1 + tolerance))
        if target_elevation_gain_m:
            tolerance = min(settings.ROUTE_RECOMMENDER_ELEVATION_TOLERANCE * multiplier, MAX_TOLERANCE)
            qs = qs.filter(
                elevation_gain_m__gte=target_elevation_gain_m * (1 - tolerance),
                elevation_gain_m__lte=target_elevation_gain_m * (1 + tolerance),
            )
        if qs.exists():
            return qs, multiplier > 1

    return base_qs.none(), True
