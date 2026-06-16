from django.db import models
from django.contrib.auth.models import User


class Route(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='routes')
    gpx_file = models.FileField(upload_to='gpx/')

    distance_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    elevation_gain_m = models.IntegerField(null=True, blank=True)
    elevation_loss_m = models.IntegerField(null=True, blank=True)
    max_elevation_m = models.IntegerField(null=True, blank=True)
    min_elevation_m = models.IntegerField(null=True, blank=True)

    track_geojson = models.JSONField(null=True, blank=True)
    elevation_profile = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['author', '-created_at'])]

    def __str__(self):
        return f'{self.title} ({self.distance_km} km)'
