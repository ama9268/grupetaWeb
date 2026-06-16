from decimal import Decimal

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Route


@receiver(post_save, sender=Route)
def update_author_stats(sender, instance, created, **kwargs):
    if not created:
        return
    profile = instance.author.profile
    profile.total_routes += 1
    if instance.distance_km:
        profile.total_km += Decimal(str(instance.distance_km))
    profile.save(update_fields=['total_routes', 'total_km'])
