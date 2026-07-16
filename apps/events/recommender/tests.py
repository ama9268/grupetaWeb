from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import Mock, patch

import pytest
import requests
from django.contrib.gis.geos import LineString, Point
from django.urls import reverse
from django.utils import timezone

from apps.groups.constants import DEFAULT_GROUP_SLUG
from apps.groups.models import Group
from apps.routes.models import Route

from . import geometry
from .exceptions import LLMUnavailable, WindDataUnavailable
from .llm.null_client import NullRouteLLM
from .llm.factory import get_llm_client
from .ranking import select_candidates
from .service import recommend_routes
from .wind import WindSample, fetch_wind_forecast, tailwind_kmh


def _default_group():
    return Group.objects.get(slug=DEFAULT_GROUP_SLUG)


# --- geometry.py: puro, sin BD ---

def test_bearing_deg_cardinal_points():
    # Puntos separados en latitud/longitud pura para que el rumbo sea exactamente cardinal.
    assert geometry.bearing_deg((0, 0), (0, 1)) == pytest.approx(90, abs=0.5)   # este
    assert geometry.bearing_deg((0, 0), (-1, 0)) == pytest.approx(180, abs=0.5)  # sur
    assert geometry.bearing_deg((0, 0), (0, -1)) == pytest.approx(270, abs=0.5)  # oeste
    assert geometry.bearing_deg((0, 0), (1, 0)) == pytest.approx(0, abs=0.5)     # norte


def test_is_loop_uses_1km_threshold_not_300m():
    # ~500 m de separación: con el umbral antiguo (300 m) NO sería circuito; con el
    # umbral corregido (1 km) SÍ debe serlo — 0.0045º de latitud ≈ 500 m.
    track = [[40.0, -3.0], [40.1, -3.0], [40.0045, -3.0]]
    assert geometry.is_loop(track, threshold_m=1000) is True
    assert geometry.is_loop(track, threshold_m=300) is False


def test_is_loop_false_for_far_apart_endpoints():
    track = [[40.0, -3.0], [41.0, -3.0]]  # ~111 km de separación
    assert geometry.is_loop(track) is False


def test_downsample_preserves_first_and_last_point():
    track = [[float(i), 0.0] for i in range(1000)]
    sampled = geometry.downsample(track, max_points=50)
    assert len(sampled) <= 50
    assert sampled[0] == track[0]
    assert sampled[-1] == track[-1]


def test_downsample_noop_under_max_points():
    track = [[0.0, 0.0], [0.1, 0.0]]
    assert geometry.downsample(track, max_points=200) == track


def test_split_by_cumulative_distance_out_and_back():
    # Ida hacia el norte y vuelta exacta por el mismo camino: el punto medio debe
    # coincidir con el punto más al norte, a la mitad de la distancia total.
    track = [[40.0, -3.0], [40.1, -3.0], [40.2, -3.0], [40.1, -3.0], [40.0, -3.0]]
    midpoint, dist_to_mid, total = geometry.split_by_cumulative_distance(track)
    assert midpoint == [40.2, -3.0]
    assert dist_to_mid == pytest.approx(total / 2, rel=0.01)


def test_analyze_track_return_bearing_is_southward_on_out_and_back():
    track = [[40.0, -3.0], [40.1, -3.0], [40.2, -3.0], [40.1, -3.0], [40.0, -3.0]]
    analysis = geometry.analyze_track(track)
    assert analysis.return_bearing_deg == pytest.approx(180, abs=1)
    assert analysis.is_loop is True


def test_analyze_track_empty():
    analysis = geometry.analyze_track([])
    assert analysis.return_bearing_deg is None
    assert analysis.is_loop is False


# --- wind.py ---

def test_tailwind_kmh_full_tailwind():
    # Viento viene del norte (from_deg=0) soplando hacia el sur; rumbo de vuelta = sur (180).
    wind = WindSample(speed_kmh=20, from_deg=0)
    assert tailwind_kmh(180, wind) == pytest.approx(20, abs=0.01)


def test_tailwind_kmh_full_headwind():
    # Viento viene del sur (from_deg=180) soplando hacia el norte; rumbo de vuelta = sur (180).
    wind = WindSample(speed_kmh=20, from_deg=180)
    assert tailwind_kmh(180, wind) == pytest.approx(-20, abs=0.01)


@patch('apps.events.recommender.wind.requests.get')
def test_fetch_wind_forecast_happy_path(mock_get):
    # Construido directamente en UTC (no vía make_aware, que usaría TIME_ZONE=Europe/Madrid
    # y desplazaría la hora) para que coincida exactamente con la hora mockeada abajo.
    at = datetime(2026, 6, 1, 10, 0, tzinfo=dt_timezone.utc)
    mock_get.return_value = Mock(
        status_code=200,
        json=lambda: {'hourly': {
            'time': ['2026-06-01T09:00', '2026-06-01T10:00', '2026-06-01T11:00'],
            'windspeed_10m': [10.0, 15.5, 12.0],
            'winddirection_10m': [90.0, 180.0, 270.0],
        }},
    )
    mock_get.return_value.raise_for_status = lambda: None
    sample = fetch_wind_forecast(lat=40.0, lon=-3.0, at=at)
    assert sample.speed_kmh == 15.5
    assert sample.from_deg == 180.0


@patch('apps.events.recommender.wind.requests.get', side_effect=requests.ConnectionError('boom'))
def test_fetch_wind_forecast_network_error_raises_unavailable(mock_get):
    with pytest.raises(WindDataUnavailable):
        fetch_wind_forecast(lat=40.0, lon=-3.0, at=timezone.now())


@patch('apps.events.recommender.wind.requests.get')
def test_fetch_wind_forecast_missing_hour_raises_unavailable(mock_get):
    mock_get.return_value = Mock(
        status_code=200,
        json=lambda: {'hourly': {'time': [], 'windspeed_10m': [], 'winddirection_10m': []}},
    )
    mock_get.return_value.raise_for_status = lambda: None
    with pytest.raises(WindDataUnavailable):
        fetch_wind_forecast(lat=40.0, lon=-3.0, at=timezone.now())


# --- ranking.py (BD real, sigue la convención del proyecto de priorizar integración) ---

@pytest.fixture
def route_factory(db, approved_moderator):
    def make(*, distance_km, elevation_gain_m=None, with_geojson=True, group=None):
        return Route.objects.create(
            group=group or _default_group(), author=approved_moderator, title=f'Ruta {distance_km}km',
            distance_km=distance_km, elevation_gain_m=elevation_gain_m,
            track_geojson=[[40.0, -3.0], [40.1, -3.0]] if with_geojson else None,
        )
    return make


@pytest.mark.django_db
def test_select_candidates_within_tolerance(route_factory):
    close = route_factory(distance_km=50)
    far = route_factory(distance_km=200)
    qs, widened = select_candidates(group=_default_group(), target_distance_km=52)
    assert list(qs) == [close]
    assert far not in qs
    assert widened is False


@pytest.mark.django_db
def test_select_candidates_widens_tolerance_when_no_exact_match(route_factory):
    # 20% de diferencia: no encaja en la tolerancia base (±15%) pero sí al ensancharla
    # x2 (±30%) — target=50, ROUTE_RECOMMENDER_DISTANCE_TOLERANCE=0.15 por defecto.
    route = route_factory(distance_km=60)
    qs, widened = select_candidates(group=_default_group(), target_distance_km=50)
    assert list(qs) == [route]
    assert widened is True


@pytest.mark.django_db
def test_select_candidates_gives_up_beyond_max_widening(route_factory):
    # 60% de diferencia: sigue sin encajar ni ensanchando hasta el tope (x3 → ±45%).
    route_factory(distance_km=80)
    qs, widened = select_candidates(group=_default_group(), target_distance_km=50)
    assert list(qs) == []
    assert widened is True


@pytest.mark.django_db
def test_select_candidates_excludes_routes_without_geojson(route_factory):
    route_factory(distance_km=50, with_geojson=False)
    qs, widened = select_candidates(group=_default_group(), target_distance_km=50)
    assert list(qs) == []


@pytest.mark.django_db
def test_select_candidates_no_targets_returns_all_group_routes(route_factory):
    a = route_factory(distance_km=10)
    b = route_factory(distance_km=200)
    qs, widened = select_candidates(group=_default_group())
    assert set(qs) == {a, b}
    assert widened is False


# --- service.py: orquestación (viento mockeado — frontera externa) ---

@pytest.mark.django_db
def test_recommend_routes_orders_by_tailwind(route_factory):
    route_a = route_factory(distance_km=50, elevation_gain_m=400)
    route_a.track_geojson = [[40.0, -3.0], [40.1, -3.0], [40.2, -3.0], [40.1, -3.0], [40.0, -3.0]]
    route_a.start_point = Point(-3.0, 40.0, srid=4326)
    route_a.track_geom = LineString([(-3.0, 40.0), (-3.0, 40.2)], srid=4326)
    route_a.save()

    def fake_wind(*, lat, lon, at):
        return WindSample(speed_kmh=20, from_deg=0)  # viento de cola en la vuelta (rumbo sur)

    with patch('apps.events.recommender.service.fetch_wind_forecast', side_effect=fake_wind):
        result = recommend_routes(
            group=_default_group(), start_at=timezone.now(), target_distance_km=50,
        )
    assert len(result.candidates) == 1
    assert result.candidates[0].wind_available is True
    assert result.candidates[0].tailwind_kmh == pytest.approx(20, abs=0.5)


@pytest.mark.django_db
def test_recommend_routes_degrades_without_500_when_wind_unavailable(route_factory):
    # Con start_point (si no, ya degrada antes de siquiera intentar pedir el viento —
    # ver test_recommend_routes_degrades_without_500_when_no_geometry).
    route = route_factory(distance_km=50)
    route.start_point = Point(-3.0, 40.0, srid=4326)
    route.save()
    with patch('apps.events.recommender.service.fetch_wind_forecast', side_effect=WindDataUnavailable('x')):
        result = recommend_routes(group=_default_group(), start_at=timezone.now(), target_distance_km=50)
    assert len(result.candidates) == 1
    assert result.candidates[0].wind_available is False
    assert result.candidates[0].tailwind_kmh is None


@pytest.mark.django_db
def test_recommend_routes_degrades_without_500_when_no_geometry(route_factory):
    # Ruta candidata sin start_point (nunca importada con geometría real): se mantiene
    # en la lista sin puntuación de viento, no rompe el resto del ranking.
    route_factory(distance_km=50)
    result = recommend_routes(group=_default_group(), start_at=timezone.now(), target_distance_km=50)
    assert len(result.candidates) == 1
    assert result.candidates[0].wind_available is False
    assert result.candidates[0].tailwind_kmh is None


# --- llm/ ---

def test_null_client_raises_llm_unavailable():
    with pytest.raises(LLMUnavailable):
        NullRouteLLM().explain(result=None)


def test_factory_defaults_to_null_client(settings):
    settings.ROUTE_RECOMMENDER_LLM_PROVIDER = 'none'
    assert isinstance(get_llm_client(), NullRouteLLM)


def test_factory_returns_anthropic_client(settings):
    settings.ROUTE_RECOMMENDER_LLM_PROVIDER = 'anthropic'
    from .llm.anthropic_client import AnthropicRouteLLM
    assert isinstance(get_llm_client(), AnthropicRouteLLM)


def test_factory_returns_ollama_client(settings):
    settings.ROUTE_RECOMMENDER_LLM_PROVIDER = 'ollama'
    from .llm.ollama_client import OllamaRouteLLM
    assert isinstance(get_llm_client(), OllamaRouteLLM)


@patch('anthropic.Anthropic')
def test_anthropic_client_explain_happy_path(mock_anthropic_cls, settings):
    from .llm.anthropic_client import AnthropicRouteLLM
    from .service import RecommendationResult

    text_block = Mock(type='text', text='Recomiendo la ruta X por el viento a favor.')
    mock_anthropic_cls.return_value.messages.create.return_value = Mock(content=[text_block])

    result = RecommendationResult(
        candidates=[], tolerance_widened=False, target_distance_km=50,
        target_elevation_gain_m=None, start_at=timezone.now(),
    )
    text = AnthropicRouteLLM().explain(result=result)
    assert 'viento a favor' in text


@patch('apps.events.recommender.llm.ollama_client.requests.post')
def test_ollama_client_explain_happy_path(mock_post):
    from .llm.ollama_client import OllamaRouteLLM
    from .service import RecommendationResult

    mock_post.return_value = Mock(status_code=200)
    mock_post.return_value.raise_for_status = lambda: None
    mock_post.return_value.json = lambda: {'message': {'content': 'Explicación local.'}}

    result = RecommendationResult(
        candidates=[], tolerance_widened=False, target_distance_km=50,
        target_elevation_gain_m=None, start_at=timezone.now(),
    )
    assert OllamaRouteLLM().explain(result=result) == 'Explicación local.'


@patch('apps.events.recommender.llm.ollama_client.requests.post', side_effect=requests.ConnectionError('down'))
def test_ollama_client_explain_raises_llm_unavailable_on_failure(mock_post):
    from .llm.ollama_client import OllamaRouteLLM
    from .service import RecommendationResult

    result = RecommendationResult(
        candidates=[], tolerance_widened=False, target_distance_km=50,
        target_elevation_gain_m=None, start_at=timezone.now(),
    )
    with pytest.raises(LLMUnavailable):
        OllamaRouteLLM().explain(result=result)


# --- Vistas del agente: permisos y degradación (ver apps/events/views.py) ---

@pytest.mark.django_db
def test_route_recommend_requires_moderator(member_client):
    response = member_client.post(reverse('salidas:route_recommend'), {
        'group': _default_group().pk,
        'start_at': (timezone.now() + timedelta(days=3)).strftime('%Y-%m-%dT%H:%M'),
    })
    assert response.status_code == 403


@pytest.mark.django_db
def test_route_recommend_blocks_moderator_of_other_group(moderator_client, db):
    other_group = Group.objects.create(name='Otra grupeta', slug='otra-grupeta')
    response = moderator_client.post(reverse('salidas:route_recommend'), {
        'group': other_group.pk,
        'start_at': (timezone.now() + timedelta(days=3)).strftime('%Y-%m-%dT%H:%M'),
    })
    assert response.status_code == 403


@pytest.mark.django_db
def test_route_recommend_missing_start_at_does_not_500(moderator_client):
    response = moderator_client.post(reverse('salidas:route_recommend'), {
        'group': _default_group().pk,
        'start_at': '',
    })
    assert response.status_code == 200


@pytest.mark.django_db
def test_route_recommend_returns_candidates(moderator_client, route_factory):
    route_factory(distance_km=50)
    with patch('apps.events.recommender.service.fetch_wind_forecast', side_effect=WindDataUnavailable('x')):
        response = moderator_client.post(reverse('salidas:route_recommend'), {
            'group': _default_group().pk,
            'start_at': (timezone.now() + timedelta(days=3)).strftime('%Y-%m-%dT%H:%M'),
            'target_distance_km': '50',
        })
    assert response.status_code == 200
    assert b'recommended_route' in response.content


@pytest.mark.django_db
def test_route_recommend_explain_degrades_without_500_when_llm_unavailable(moderator_client, route_factory):
    route_factory(distance_km=50)
    response = moderator_client.post(reverse('salidas:route_recommend_explain'), {
        'group': _default_group().pk,
        'start_at': (timezone.now() + timedelta(days=3)).strftime('%Y-%m-%dT%H:%M'),
        'target_distance_km': '50',
    })
    assert response.status_code == 200
    assert b'No se pudo generar la explicaci' in response.content
