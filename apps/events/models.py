from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from apps.groups.querysets import GroupScopedQuerySet


class Event(models.Model):
    class State(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        REALIZADO = 'realizado', 'Realizado'
        ARCHIVADO = 'archivado', 'Archivado'

    class EventType(models.TextChoices):
        RUTA_ESPECIAL = 'ruta_especial', 'Ruta especial'
        VIAJE = 'viaje', 'Viaje'
        CARRERA = 'carrera', 'Carrera'
        OTRO = 'otro', 'Otro'

    class PaceLevel(models.TextChoices):
        SUAVE = 'suave', 'Suave'
        MEDIO = 'medio', 'Medio'
        FUERTE = 'fuerte', 'Fuerte'

    # Estados que se muestran por defecto en el listado (activos/próximos).
    DEFAULT_LIST_STATES = (State.PENDIENTE,)

    group = models.ForeignKey(
        'groups.Group', on_delete=models.PROTECT, related_name='events'
    )
    objects = GroupScopedQuerySet.as_manager()

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    event_type = models.CharField(
        max_length=20, choices=EventType.choices, default=EventType.OTRO
    )
    image_public_id = models.CharField(max_length=200, blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    start_at = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True)
    state = models.CharField(
        max_length=20, choices=State.choices, default=State.PENDIENTE
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='created_events'
    )
    associated_route = models.ForeignKey(
        'routes.Route', on_delete=models.SET_NULL, null=True, blank=True, related_name='events'
    )
    chat_room = models.OneToOneField(
        'chat.ChatRoom', on_delete=models.SET_NULL, null=True, blank=True, related_name='event'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Campos específicos de "Salidas" (event_type=RUTA_ESPECIAL); quedan vacíos/blank para
    # el resto de tipos de evento. Ver apps/events/CLAUDE.md, sección "Salidas".
    pace_level = models.CharField(max_length=20, choices=PaceLevel.choices, blank=True)
    target_distance_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    target_elevation_gain_m = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['start_at']
        indexes = [
            models.Index(fields=['start_at'], name='events_event_start_at_idx'),
            models.Index(fields=['state'], name='events_event_state_idx'),
            models.Index(fields=['group', 'start_at'], name='events_event_group_start_idx'),
        ]

    def __str__(self):
        # start_at llega de la BD en UTC (aware); localtime() lo pasa a hora de
        # TIME_ZONE antes de formatear — un .strftime() directo mostraría la hora UTC
        # cruda, desfasada respecto a la hora local (ver apps/events/CLAUDE.md).
        return f'{self.title} ({timezone.localtime(self.start_at).strftime("%d/%m/%Y")})'

    def get_absolute_url(self):
        """Salidas (ruta_especial) y el resto de eventos viven en la misma tabla pero se
        navegan desde secciones distintas (ver apps/events/CLAUDE.md, "Salidas") — esta es
        la única fuente de verdad de a qué namespace enlazar, para no repetir el `if` en
        cada plantilla o vista que necesite enlazar a la ficha de un evento."""
        from django.urls import reverse
        namespace = 'salidas' if self.event_type == self.EventType.RUTA_ESPECIAL else 'events'
        return reverse(f'{namespace}:detail', args=[self.pk])

    @property
    def is_upcoming(self):
        return self.start_at >= timezone.now()

    @property
    def album(self):
        """Álbum de fotos/vídeos del evento (uno por evento). None si aún no existe."""
        return self.albums.first()

    def attending_count(self):
        return self.rsvps.filter(response=EventRSVP.Response.SI).count()

    def mark_realizado(self, by_user):
        """Marca el evento/salida como realizado (manual, Admin/Moderador) y crea su
        álbum si no existe. Solo alcanzable desde PENDIENTE (idempotente)."""
        if self.state != self.State.PENDIENTE:
            return
        self.state = self.State.REALIZADO
        self.save(update_fields=['state'])
        if not self.albums.exists():
            from apps.media_gallery.models import Album
            Album.objects.create(
                title=f'{self.title} — {timezone.localtime(self.start_at):%d/%m/%Y}',
                event=self,
                group=self.group,
                created_by=by_user,
            )

    def archive(self):
        """Archiva el evento/salida en solo lectura (manual, Admin/Moderador).
        Alcanzable desde PENDIENTE o REALIZADO (idempotente). Nunca crea álbum."""
        if self.state == self.State.ARCHIVADO:
            return
        self.state = self.State.ARCHIVADO
        self.save(update_fields=['state'])
        if self.chat_room and not self.chat_room.is_archived:
            self.chat_room.is_archived = True
            self.chat_room.save(update_fields=['is_archived'])


class EventRSVP(models.Model):
    class Response(models.TextChoices):
        SI = 'si', 'Voy'
        NO = 'no', 'No voy'
        QUIZAS = 'quizas', 'Quizás'

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='rsvps')
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rsvps')
    response = models.CharField(max_length=20, choices=Response.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('event', 'member')]

    def __str__(self):
        return f'{self.member} → {self.event} ({self.response})'
