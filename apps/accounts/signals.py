from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

from .models import UserProfile
from .emails import send_approval_request_email


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if not created:
        return
    UserProfile.objects.create(user=instance)
    if not instance.is_active:
        send_approval_request_email(instance)
