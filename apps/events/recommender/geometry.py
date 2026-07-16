"""Geometría pura de una ruta: rumbo del tramo de vuelta, si es un circuito cerrado.

Trabaja sobre `Route.track_geojson` (lista de pares `[lat, lon]`) ya cargado en memoria —
no usa PostGIS/GEOS: "rumbo entre dos puntos" no es una operación espacial que PostGIS
resuelva mejor que trigonometría esférica estándar, y así queda testeable sin BD. Sin
dependencias de Django: puro Python, coste acotado por `downsample`.
"""
import math
from dataclasses import dataclass

EARTH_RADIUS_KM = 6371.0


def downsample(track, max_points=200):
    """Reduce `track` a como máximo `max_points` puntos equiespaciados, preservando
    siempre el primer y el último punto exactos (de ellos depende `is_loop` y el extremo
    del tramo de vuelta). Cota dura de coste: el resto de funciones de este módulo pasan
    a ser O(max_points) sin importar la densidad real del GPX (puede tener miles de
    puntos)."""
    if len(track) <= max_points:
        return list(track)
    stride = len(track) / max_points
    sampled = [track[int(i * stride)] for i in range(max_points)]
    sampled[-1] = track[-1]
    return sampled


def haversine_distance_km(p1, p2):
    lat1, lon1 = math.radians(p1[0]), math.radians(p1[1])
    lat2, lon2 = math.radians(p2[0]), math.radians(p2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def bearing_deg(p1, p2):
    """Rumbo inicial en grados [0, 360) de p1 a p2 (fórmula esférica estándar)."""
    lat1, lon1 = math.radians(p1[0]), math.radians(p1[1])
    lat2, lon2 = math.radians(p2[0]), math.radians(p2[1])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def is_loop(track, threshold_m=1000):
    """True si el punto de inicio y el final del track están a menos de `threshold_m`
    uno de otro (circuito cerrado). Umbral por defecto: 1 km — 300 m es demasiado
    estricto para un GPX real, donde el punto de "cierre" rara vez coincide con
    precisión de pocos metros. Se calcula sobre los extremos reales del track completo
    (operación O(1), no hace falta downsample)."""
    if len(track) < 2:
        return False
    return haversine_distance_km(track[0], track[-1]) * 1000 <= threshold_m


def split_by_cumulative_distance(track):
    """Parte `track` por el punto más cercano al 50% de su distancia acumulada.
    Devuelve `(punto_medio, distancia_a_medio_km, distancia_total_km)`, o `None` si el
    track tiene menos de 2 puntos."""
    if len(track) < 2:
        return None
    cumulative = [0.0]
    for a, b in zip(track, track[1:]):
        cumulative.append(cumulative[-1] + haversine_distance_km(a, b))
    total = cumulative[-1]
    half = total / 2
    mid_index = min(range(len(cumulative)), key=lambda i: abs(cumulative[i] - half))
    return track[mid_index], cumulative[mid_index], total


@dataclass
class TrackAnalysis:
    is_loop: bool
    return_bearing_deg: float | None
    distance_to_midpoint_km: float | None
    total_distance_km: float


def analyze_track(track, max_points=200, loop_threshold_m=1000):
    """Analiza un track (lista de `[lat, lon]`) en una sola pasada: si es un circuito
    cerrado, el rumbo del tramo de vuelta y la distancia hasta el punto medio (usada por
    `recommender.service` para estimar en qué instante se alcanza ese tramo).

    El rumbo de vuelta = bearing en línea recta del punto medio (50% de distancia
    acumulada) al último punto. Vale tanto para ida-y-vuelta como para bucles (en ambos
    casos el último tramo "vuelve" hacia el origen). Limitación conocida: es un único
    escalar para todo el tramo — en circuitos con varios cambios de dirección (p.ej. un
    rectángulo) es una aproximación, no garantiza viento de cola en todo el recorrido.
    """
    if not track or len(track) < 2:
        return TrackAnalysis(
            is_loop=False, return_bearing_deg=None, distance_to_midpoint_km=None, total_distance_km=0.0,
        )

    loop = is_loop(track, threshold_m=loop_threshold_m)
    sampled = downsample(track, max_points)
    split = split_by_cumulative_distance(sampled)
    if split is None:
        return TrackAnalysis(
            is_loop=loop, return_bearing_deg=None, distance_to_midpoint_km=None, total_distance_km=0.0,
        )
    midpoint, distance_to_mid, total = split
    bearing = bearing_deg(midpoint, sampled[-1])
    return TrackAnalysis(
        is_loop=loop, return_bearing_deg=bearing, distance_to_midpoint_km=distance_to_mid, total_distance_km=total,
    )
