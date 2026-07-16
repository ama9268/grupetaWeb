from django.db import models
from django.contrib.auth.models import User

from apps.groups.querysets import GroupScopedQuerySet


class Album(models.Model):
    objects = GroupScopedQuerySet.as_manager()

    # FK directa (no solo derivada de `event`, que es nullable): evita fugas de
    # datos entre grupetas si algún día se olvida un JOIN hasta el evento.
    group = models.ForeignKey(
        'groups.Group', on_delete=models.PROTECT, related_name='albums'
    )
    title = models.CharField(max_length=200)
    event = models.ForeignKey(
        'events.Event', on_delete=models.SET_NULL, null=True, blank=True, related_name='albums'
    )
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='albums')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class MediaItem(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('image', 'Imagen'),
        ('video', 'Vídeo'),
    ]

    objects = GroupScopedQuerySet.as_manager()

    # FK directa (no solo derivada de `album`, que es nullable): mismo motivo
    # que en Album.group.
    group = models.ForeignKey(
        'groups.Group', on_delete=models.PROTECT, related_name='media_items'
    )
    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name='items', null=True, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='media_items')
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES)
    cloudinary_public_id = models.CharField(max_length=200)
    cloudinary_url = models.URLField(max_length=500)
    title = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['group', '-created_at'], name='media_item_group_created_idx'),
        ]

    def __str__(self):
        return self.title or self.cloudinary_public_id
