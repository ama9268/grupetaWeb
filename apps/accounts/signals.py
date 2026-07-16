from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

from .models import UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if not created:
        return
    UserProfile.objects.create(user=instance)
    # El aviso de "solicitud pendiente" se dispara desde apps.groups.signals
    # cuando se crea la Membership (que sabe a qué grupeta concreta avisar).
