from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import EventRSVP


@receiver(pre_save, sender=EventRSVP)
def capture_previous_rsvp(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._previous_response = EventRSVP.objects.get(pk=instance.pk).response
        except EventRSVP.DoesNotExist:
            instance._previous_response = None
    else:
        instance._previous_response = None


@receiver(post_save, sender=EventRSVP)
def update_events_attended(sender, instance, created, **kwargs):
    previous = getattr(instance, '_previous_response', None)
    current = instance.response
    profile = instance.user.profile

    if current == 'attending' and previous != 'attending':
        profile.total_events_attended += 1
        profile.save(update_fields=['total_events_attended'])
    elif current == 'not_attending' and previous == 'attending':
        profile.total_events_attended = max(0, profile.total_events_attended - 1)
        profile.save(update_fields=['total_events_attended'])
