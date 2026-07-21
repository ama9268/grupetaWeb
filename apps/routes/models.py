from django.contrib.auth.models import User
from django.contrib.gis.db import models as gis_models
from django.db import models

from apps.groups.querysets import GroupScopedQuerySet


class Route(gis_models.Model):
    class Difficulty(models.TextChoices):
        SUAVE = 'suave', 'Suave'
        MEDIA = 'media', 'Media'
        DURA = 'dura', 'Dura'

    group = models.ForeignKey(
        'groups.Group', on_delete=models.PROTECT, related_name='routes'
    )
    objects = GroupScopedQuerySet.as_manager()

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    difficulty = models.CharField(max_length=10, choices=Difficulty.choices, blank=True)
    recommendable_for_salidas = models.BooleanField(
        default=True,
        verbose_name='Recomendable para Salidas',
        help_text=(
            'Desmárcala si es una ruta puntual (p.ej. un viaje lejano) que no debe '
            'sugerirse para las Salidas habituales de la grupeta.'
        ),
    )
    is_archived = models.BooleanField(
        default=False,
        verbose_name='Archivada',
        help_text=(
            'Una ruta archivada desaparece del catálogo y de las recomendaciones de '
            'Salidas, pero se conserva (no se puede eliminar una ruta que ya ha '
            'participado en algún evento/Salida, para no perder su historial).'
        ),
    )
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='routes')
    gpx_file = models.FileField(upload_to='gpx/', blank=True)

    distance_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    elevation_gain_m = models.IntegerField(null=True, blank=True)
    elevation_loss_m = models.IntegerField(null=True, blank=True)
    max_elevation_m = models.IntegerField(null=True, blank=True)
    min_elevation_m = models.IntegerField(null=True, blank=True)

    # Contrato de datos hacia Leaflet/Chart.js (templates/routes/partials/route_map.html):
    # lista de pares [lat, lon] y de puntos {d, e} del perfil de elevación.
    track_geojson = models.JSONField(null=True, blank=True)
    elevation_profile = models.JSONField(null=True, blank=True)

    # Geometría real (PostGIS), usada para la detección de rutas duplicadas dentro
    # de la misma grupeta (apps/routes/dedup.py). No sustituye a `track_geojson`.
    track_geom = gis_models.LineStringField(geography=True, srid=4326, null=True, blank=True)
    start_point = gis_models.PointField(geography=True, srid=4326, null=True, blank=True)

    # Solo se rellena si la ruta viene de una importación de Strava; evita
    # reimportar la misma actividad dos veces (apps/routes/strava.py).
    strava_activity_id = models.BigIntegerField(null=True, blank=True, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['author', '-created_at']),
            models.Index(fields=['group', 'distance_km']),
        ]

    def __str__(self):
        return f'{self.title} ({self.distance_km} km)'

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('routes:detail', args=[self.pk])


class StravaAccount(models.Model):
    """Cuenta de Strava vinculada a un usuario (siempre Moderador/Admin, ver permisos
    en las vistas). Tokens cifrados con Fernet (apps/routes/strava.py)."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='strava_account')
    access_token_encrypted = models.TextField()
    refresh_token_encrypted = models.TextField()
    expires_at = models.DateTimeField()
    strava_athlete_id = models.BigIntegerField(unique=True)
    connected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Strava de {self.user}'


class StravaImportCandidate(models.Model):
    """Actividad de Strava en revisión antes de convertirse en una `Route`.

    Se sincroniza manualmente (botón "Sincronizar"), no hay tarea programada
    (ver apps/routes/CLAUDE.md, sección "Fuera de alcance").
    """

    class Status(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        IMPORTADO = 'importado', 'Importado'
        DESCARTADO = 'descartado', 'Descartado'

    account = models.ForeignKey(StravaAccount, on_delete=models.CASCADE, related_name='candidates')
    strava_activity_id = models.BigIntegerField(unique=True)
    name = models.CharField(max_length=200)
    distance_km = models.DecimalField(max_digits=6, decimal_places=2)
    elevation_gain_m = models.IntegerField(null=True, blank=True)
    moving_time_s = models.IntegerField(null=True, blank=True)
    sport_type = models.CharField(max_length=50, blank=True)
    start_point = gis_models.PointField(geography=True, srid=4326, null=True, blank=True)
    started_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDIENTE)
    imported_route = models.ForeignKey(
        Route, on_delete=models.SET_NULL, null=True, blank=True, related_name='strava_candidate'
    )
    staged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-started_at']
        indexes = [models.Index(fields=['account', 'status'])]

    def __str__(self):
        return f'{self.name} ({self.get_status_display()})'
