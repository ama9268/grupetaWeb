from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import Mock, patch

import pytest
import requests
from django.contrib.gis.geos import LineString, Point
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from apps.groups.constants import DEFAULT_GROUP_SLUG
from apps.groups.models import Group
from apps.routes.models import Route

from .models import Event
from .weather import WeatherDataUnavailable, fetch_weather_forecast, fetch_wind_grid


def _default_group():
    return Group.objects.get(slug=DEFAULT_GROUP_SLUG)


@pytest.fixture(autouse=True)
def _clear_cache():
    # Cada test usa su propio (lat, lon, fecha, hora) para no compartir clave de caché
    # con otro test, pero se limpia igualmente por si acaso (LocMemCache es por
    # proceso y persiste entre tests si no se limpia explícitamente).
    cache.clear()
    yield
    cache.clear()


HOURLY_TEMPLATE = {
    'time': ['2026-06-01T09:00', '2026-06-01T10:00', '2026-06-01T11:00'],
    'temperature_2m': [18.0, 22.5, 25.0],
    'precipitation_probability': [10, 5, 0],
    'weathercode': [1, 61, 0],
    'windspeed_10m': [10.0, 15.5, 12.0],
    'winddirection_10m': [90.0, 180.0, 270.0],
}


# --- fetch_weather_forecast ---

@patch('apps.events.weather.requests.get')
def test_fetch_weather_forecast_happy_path(mock_get):
    at = datetime(2026, 6, 1, 10, 0, tzinfo=dt_timezone.utc)
    mock_get.return_value = Mock(status_code=200, json=lambda: {'hourly': HOURLY_TEMPLATE})
    mock_get.return_value.raise_for_status = lambda: None

    sample = fetch_weather_forecast(lat=40.0, lon=-3.0, at=at)

    assert sample.temperature_c == 22.5
    assert sample.sky_description == 'Lluvia débil'
    assert sample.sky_icon == 'rain'
    assert sample.precipitation_probability_pct == 5.0
    assert sample.wind_speed_kmh == 15.5
    assert sample.wind_from_deg == 180.0


@patch('apps.events.weather.requests.get', side_effect=requests.ConnectionError('boom'))
def test_fetch_weather_forecast_network_error_raises_unavailable(mock_get):
    with pytest.raises(WeatherDataUnavailable):
        fetch_weather_forecast(lat=40.0, lon=-3.0, at=timezone.now())


@patch('apps.events.weather.requests.get')
def test_fetch_weather_forecast_missing_hour_raises_unavailable(mock_get):
    mock_get.return_value = Mock(status_code=200, json=lambda: {'hourly': {
        'time': [], 'temperature_2m': [], 'precipitation_probability': [],
        'weathercode': [], 'windspeed_10m': [], 'winddirection_10m': [],
    }})
    mock_get.return_value.raise_for_status = lambda: None
    with pytest.raises(WeatherDataUnavailable):
        fetch_weather_forecast(lat=41.0, lon=-4.0, at=timezone.now())


@patch('apps.events.weather.requests.get')
def test_fetch_weather_forecast_unknown_weathercode_falls_back(mock_get):
    at = datetime(2026, 6, 2, 10, 0, tzinfo=dt_timezone.utc)
    hourly = dict(HOURLY_TEMPLATE, time=['2026-06-02T10:00'], weathercode=[9999],
                  temperature_2m=[20.0], precipitation_probability=[0],
                  windspeed_10m=[5.0], winddirection_10m=[0.0])
    mock_get.return_value = Mock(status_code=200, json=lambda: {'hourly': hourly})
    mock_get.return_value.raise_for_status = lambda: None

    sample = fetch_weather_forecast(lat=42.0, lon=-5.0, at=at)
    assert sample.sky_description == 'Sin datos'
    assert sample.sky_icon == 'cloud'


# --- fetch_wind_grid ---

def _grid_point(speed=10.0, direction=90.0, hour='2026-06-01T10:00'):
    return {'hourly': {'time': [hour], 'windspeed_10m': [speed], 'winddirection_10m': [direction]}}


@patch('apps.events.weather.requests.get')
def test_fetch_wind_grid_happy_path_shape(mock_get):
    at = datetime(2026, 6, 1, 10, 0, tzinfo=dt_timezone.utc)
    points = [_grid_point() for _ in range(100)]  # resolución 10x10
    mock_get.return_value = Mock(status_code=200, json=lambda: points)
    mock_get.return_value.raise_for_status = lambda: None

    grid = fetch_wind_grid(min_lat=40.0, min_lon=-4.0, max_lat=40.5, max_lon=-3.5, at=at)

    assert len(grid) == 2  # componentes U y V
    assert grid[0]['header']['nx'] == 10
    assert grid[0]['header']['ny'] == 10
    assert len(grid[0]['data']) == 100
    assert len(grid[1]['data']) == 100


@patch('apps.events.weather.requests.get')
def test_fetch_wind_grid_incomplete_response_raises_unavailable(mock_get):
    at = datetime(2026, 6, 3, 10, 0, tzinfo=dt_timezone.utc)
    mock_get.return_value = Mock(status_code=200, json=lambda: [_grid_point()])  # solo 1 de 100
    mock_get.return_value.raise_for_status = lambda: None
    with pytest.raises(WeatherDataUnavailable):
        fetch_wind_grid(min_lat=41.0, min_lon=-5.0, max_lat=41.5, max_lon=-4.5, at=at)


@patch('apps.events.weather.requests.get', side_effect=requests.ConnectionError('boom'))
def test_fetch_wind_grid_network_error_raises_unavailable(mock_get):
    with pytest.raises(WeatherDataUnavailable):
        fetch_wind_grid(min_lat=39.0, min_lon=-6.0, max_lat=39.5, max_lon=-5.5, at=timezone.now())


# --- events:wind_grid (vista) + EventDetailView (contexto weather/wind_grid_url) ---

@pytest.fixture
def route_with_geom(approved_moderator):
    track = LineString([(-3.70, 40.40), (-3.65, 40.45)], srid=4326)
    return Route.objects.create(
        group=_default_group(), author=approved_moderator, title='Ruta con geometría',
        track_geojson=[[40.40, -3.70], [40.45, -3.65]],
        track_geom=track, start_point=Point(-3.70, 40.40, srid=4326),
    )


@pytest.fixture
def event_with_route(approved_moderator, route_with_geom):
    return Event.objects.create(
        title='Con ruta y geometría', event_type=Event.EventType.OTRO,
        start_at=timezone.now() + timedelta(days=5),
        created_by=approved_moderator, group=_default_group(), associated_route=route_with_geom,
    )


@pytest.mark.django_db
def test_wind_grid_endpoint_404_without_associated_route(member_client, approved_moderator):
    event = Event.objects.create(
        title='Sin ruta', event_type=Event.EventType.OTRO,
        start_at=timezone.now() + timedelta(days=5),
        created_by=approved_moderator, group=_default_group(),
    )
    response = member_client.get(reverse('events:wind_grid', args=[event.pk]))
    assert response.status_code == 404


@pytest.mark.django_db
@patch('apps.events.weather.requests.get')
def test_wind_grid_endpoint_returns_grid_json(mock_get, member_client, event_with_route):
    points = [_grid_point(hour=timezone.localtime(event_with_route.start_at, dt_timezone.utc).strftime('%Y-%m-%dT%H:00')) for _ in range(100)]
    mock_get.return_value = Mock(status_code=200, json=lambda: points)
    mock_get.return_value.raise_for_status = lambda: None

    response = member_client.get(reverse('events:wind_grid', args=[event_with_route.pk]))
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.django_db
@patch('apps.events.weather.requests.get', side_effect=requests.ConnectionError('boom'))
def test_wind_grid_endpoint_502_when_forecast_unavailable(mock_get, member_client, event_with_route):
    response = member_client.get(reverse('events:wind_grid', args=[event_with_route.pk]))
    assert response.status_code == 502
    assert 'error' in response.json()


@pytest.mark.django_db
def test_wind_grid_endpoint_requires_group_membership(client, event_with_route):
    # Aprobado en OTRA grupeta (no en la del evento): pasa @approved_required pero debe
    # chocar con require_group_member — 403, no la redirección de "pendiente de aprobación".
    from django.contrib.auth.models import User
    from apps.groups.models import Group, Membership

    other_group = Group.objects.create(name='Otra Grupeta', slug='otra-grupeta')
    outsider = User.objects.create_user(username='outsider@test.com', email='outsider@test.com', password='testpass123')
    Membership.objects.create(user=outsider, group=other_group, role=Membership.Role.MEMBER, status=Membership.Status.APPROVED)
    client.login(username='outsider@test.com', password='testpass123')

    response = client.get(reverse('events:wind_grid', args=[event_with_route.pk]))
    assert response.status_code == 403


@pytest.mark.django_db
@patch('apps.events.weather.requests.get')
def test_event_detail_context_includes_weather_when_route_has_coords(mock_get, member_client, event_with_route):
    at_utc = timezone.localtime(event_with_route.start_at, dt_timezone.utc)
    hourly = dict(HOURLY_TEMPLATE, time=[at_utc.strftime('%Y-%m-%dT%H:00')],
                  temperature_2m=[20.0], precipitation_probability=[0], weathercode=[0],
                  windspeed_10m=[8.0], winddirection_10m=[45.0])
    mock_get.return_value = Mock(status_code=200, json=lambda: {'hourly': hourly})
    mock_get.return_value.raise_for_status = lambda: None

    response = member_client.get(reverse('events:detail', args=[event_with_route.pk]))
    assert response.status_code == 200
    assert response.context['weather'] is not None
    assert response.context['weather'].temperature_c == 20.0
    assert response.context['weather'].sky_icon == 'sun'
    assert response.context['wind_grid_url'] == reverse('events:wind_grid', args=[event_with_route.pk])
    assert 'Previsión meteorológica'.encode() in response.content
    assert b'toggle-wind' in response.content


@pytest.mark.django_db
def test_event_detail_context_weather_none_without_route(member_client, approved_moderator):
    event = Event.objects.create(
        title='Sin ruta ni viento', event_type=Event.EventType.OTRO,
        start_at=timezone.now() + timedelta(days=5),
        created_by=approved_moderator, group=_default_group(),
    )
    response = member_client.get(reverse('events:detail', args=[event.pk]))
    assert response.status_code == 200
    assert response.context['weather'] is None
    assert response.context['wind_grid_url'] is None
    assert b'toggle-wind' not in response.content


@pytest.mark.django_db
@patch('apps.events.weather.requests.get', side_effect=requests.ConnectionError('boom'))
def test_event_detail_shows_fallback_message_when_forecast_unavailable(mock_get, member_client, event_with_route):
    response = member_client.get(reverse('events:detail', args=[event_with_route.pk]))
    assert response.status_code == 200
    assert response.context['weather'] is None
    assert 'no disponible'.encode('utf-8') in response.content
