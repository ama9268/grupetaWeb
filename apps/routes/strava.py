"""Integración con Strava: OAuth, listado de actividades y descarga de streams.

Dos capas en un único fichero — a diferencia de RutasG (que las separaba en
`lib/services/strava.py` + `rides/strava_service.py` porque tenía 2-3 consumidores:
web, API DRF, comando de management), aquí solo hay un consumidor (las vistas de
`apps/routes/views.py`), así que no hace falta repartir en varios ficheros:

- `StravaClient`: envoltorio fino sobre `stravalib.Client`, sin dependencias de Django.
- `StravaService`: puente Django — lee/escribe tokens cifrados en `StravaAccount`.
"""
from datetime import datetime, timedelta, timezone as dt_timezone

import gpxpy.gpx
from cryptography.fernet import Fernet
from django.conf import settings
from django.utils import timezone
from stravalib.client import Client

from .models import StravaAccount

# Solo actividades ciclistas; el resto (running, natación...) no interesa a "rutas".
BIKE_SPORT_TYPES = {'Ride', 'MountainBikeRide', 'EBikeRide', 'GravelRide'}

TOKEN_REFRESH_MARGIN = timedelta(minutes=5)


def _fernet():
    return Fernet(settings.STRAVA_ENCRYPTION_KEY)


def encrypt_token(raw):
    return _fernet().encrypt(raw.encode()).decode()


def decrypt_token(encrypted):
    return _fernet().decrypt(encrypted.encode()).decode()


def _expires_at_from(access_info):
    return datetime.fromtimestamp(access_info['expires_at'], tz=dt_timezone.utc)


def sport_type_str(activity):
    """Extrae el valor de texto plano de `activity.sport_type`.

    stravalib envuelve `sport_type` en `RelaxedSportType`, un modelo Pydantic
    que sobrescribe `__eq__` pero no `__hash__` (no se puede usar `in <set>`
    directamente) y cuyo `str()` por defecto da `"root='Ride'"`, no `"Ride"`.
    """
    value = getattr(activity.sport_type, 'root', activity.sport_type)
    return value or ''


def build_gpx_from_streams(streams, started_at):
    """Convierte los streams de detalle de una actividad de Strava (latlng,
    altitude, time) en un objeto `gpxpy.gpx.GPX` — mismo tipo que produce
    `gpxpy.parse()` al subir un GPX directo, para reutilizar íntegramente
    `apps.routes.gpx_utils.extract_gpx_stats` (una sola implementación de la
    extracción de estadísticas, sin duplicarla por origen del track como hacía
    RutasG entre su vista web y su API).
    """
    latlng = streams['latlng'].data if 'latlng' in streams else []
    altitude = streams['altitude'].data if 'altitude' in streams else []
    times = streams['time'].data if 'time' in streams else []

    gpx = gpxpy.gpx.GPX()
    track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(track)
    segment = gpxpy.gpx.GPXTrackSegment()
    track.segments.append(segment)

    for i, (lat, lon) in enumerate(latlng):
        elevation = altitude[i] if i < len(altitude) else None
        offset = times[i] if i < len(times) else None
        point_time = started_at + timedelta(seconds=offset) if offset is not None else None
        segment.points.append(
            gpxpy.gpx.GPXTrackPoint(lat, lon, elevation=elevation, time=point_time)
        )

    return gpx


class StravaClient:
    """Envoltorio fino sobre `stravalib.Client`, sin estado de Django."""

    def __init__(self, access_token=None, refresh_token=None):
        self.client = Client(access_token=access_token, refresh_token=refresh_token)

    def authorization_url(self, state):
        return self.client.authorization_url(
            client_id=settings.STRAVA_CLIENT_ID,
            redirect_uri=settings.STRAVA_REDIRECT_URI,
            scope=['activity:read_all'],
            state=state,
        )

    def exchange_code_for_token(self, code):
        return self.client.exchange_code_for_token(
            client_id=settings.STRAVA_CLIENT_ID,
            client_secret=settings.STRAVA_CLIENT_SECRET,
            code=code,
            return_athlete=True,
        )

    def refresh_access_token(self, refresh_token):
        return self.client.refresh_access_token(
            client_id=settings.STRAVA_CLIENT_ID,
            client_secret=settings.STRAVA_CLIENT_SECRET,
            refresh_token=refresh_token,
        )

    def list_recent_ride_activities(self, days=180):
        after = timezone.now() - timedelta(days=days)
        for activity in self.client.get_activities(after=after):
            if sport_type_str(activity) in BIKE_SPORT_TYPES:
                yield activity

    def get_activity_streams(self, activity_id):
        return self.client.get_activity_streams(
            activity_id, types=['latlng', 'altitude', 'time'], resolution='high',
        )


class StravaService:
    """Puente Django: gestiona el `StravaAccount` del usuario (tokens cifrados)."""

    def __init__(self, account: StravaAccount | None = None):
        self.account = account

    def authorization_url(self, state):
        return StravaClient().authorization_url(state)

    def connect(self, user, code):
        """Intercambia el código de autorización y crea/actualiza el StravaAccount."""
        access_info, athlete = StravaClient().exchange_code_for_token(code)
        account, _ = StravaAccount.objects.update_or_create(
            user=user,
            defaults={
                'access_token_encrypted': encrypt_token(access_info['access_token']),
                'refresh_token_encrypted': encrypt_token(access_info['refresh_token']),
                'expires_at': _expires_at_from(access_info),
                'strava_athlete_id': athlete.id,
            },
        )
        self.account = account
        return account

    def _refresh_token_if_needed(self):
        if timezone.now() + TOKEN_REFRESH_MARGIN < self.account.expires_at:
            return
        refresh_token = decrypt_token(self.account.refresh_token_encrypted)
        access_info = StravaClient().refresh_access_token(refresh_token)
        self.account.access_token_encrypted = encrypt_token(access_info['access_token'])
        self.account.refresh_token_encrypted = encrypt_token(access_info['refresh_token'])
        self.account.expires_at = _expires_at_from(access_info)
        self.account.save(update_fields=['access_token_encrypted', 'refresh_token_encrypted', 'expires_at'])

    def _client(self):
        self._refresh_token_if_needed()
        return StravaClient(
            access_token=decrypt_token(self.account.access_token_encrypted),
            refresh_token=decrypt_token(self.account.refresh_token_encrypted),
        )

    def list_recent_activities(self, days=180):
        return self._client().list_recent_ride_activities(days=days)

    def get_activity_streams(self, activity_id):
        return self._client().get_activity_streams(activity_id)
