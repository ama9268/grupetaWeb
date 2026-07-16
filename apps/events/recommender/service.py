"""Orquestador del agente de recomendación de ruta: filtra candidatas (`ranking.py`),
calcula la favorabilidad del viento en el tramo de vuelta de cada una (`geometry.py` +
`wind.py`) y devuelve un ranking 100% determinista. El LLM (opcional, ver `llm/`) solo
narra este resultado ya calculado — nunca decide el orden ni inventa cifras.
"""
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Optional

from django.conf import settings

from . import geometry
from .exceptions import WindDataUnavailable
from .ranking import select_candidates
from .wind import fetch_wind_forecast, tailwind_kmh


@dataclass
class CandidateScore:
    route: object  # apps.routes.models.Route
    tailwind_kmh: Optional[float]  # None si no se pudo calcular (sin geometría o sin viento)
    is_loop: bool
    wind_available: bool


@dataclass
class RecommendationResult:
    candidates: list  # list[CandidateScore], ya ordenada (favorable primero)
    tolerance_widened: bool
    target_distance_km: Optional[Decimal]
    target_elevation_gain_m: Optional[int]
    start_at: object


def _estimate_return_leg_at(start_at, distance_to_midpoint_km):
    avg_speed_kmh = settings.ROUTE_RECOMMENDER_AVG_SPEED_KMH
    hours = (distance_to_midpoint_km or 0) / avg_speed_kmh
    return start_at + timedelta(hours=hours)


def _score_candidate(route, start_at):
    analysis = geometry.analyze_track(
        route.track_geojson or [], max_points=settings.ROUTE_RECOMMENDER_MAX_TRACK_POINTS,
    )
    if analysis.return_bearing_deg is None or not route.start_point:
        return CandidateScore(route=route, tailwind_kmh=None, is_loop=analysis.is_loop, wind_available=False)

    return_leg_at = _estimate_return_leg_at(start_at, analysis.distance_to_midpoint_km)
    try:
        wind = fetch_wind_forecast(lat=route.start_point.y, lon=route.start_point.x, at=return_leg_at)
    except WindDataUnavailable:
        return CandidateScore(route=route, tailwind_kmh=None, is_loop=analysis.is_loop, wind_available=False)

    favorability = tailwind_kmh(analysis.return_bearing_deg, wind)
    return CandidateScore(route=route, tailwind_kmh=favorability, is_loop=analysis.is_loop, wind_available=True)


def recommend_routes(*, group, start_at, target_distance_km=None, target_elevation_gain_m=None):
    """Punto de entrada único del agente (también el único punto donde se podría
    enganchar en el futuro una auditoría de recomendaciones — ver apps/events/CLAUDE.md,
    sección "Salidas", "Fuera de alcance")."""
    candidates_qs, tolerance_widened = select_candidates(
        group=group, target_distance_km=target_distance_km, target_elevation_gain_m=target_elevation_gain_m,
    )
    scored = [_score_candidate(route, start_at) for route in candidates_qs]

    def sort_key(candidate):
        # Con viento primero (favorable → desfavorable); sin datos de viento, al final,
        # desempatando por cercanía a la distancia objetivo.
        target = float(target_distance_km) if target_distance_km else float(candidate.route.distance_km or 0)
        distance_gap = abs(float(candidate.route.distance_km or 0) - target)
        return (candidate.tailwind_kmh is None, -(candidate.tailwind_kmh or 0), distance_gap)

    scored.sort(key=sort_key)

    return RecommendationResult(
        candidates=scored[:settings.ROUTE_RECOMMENDER_MAX_CANDIDATES],
        tolerance_widened=tolerance_widened,
        target_distance_km=target_distance_km,
        target_elevation_gain_m=target_elevation_gain_m,
        start_at=start_at,
    )
