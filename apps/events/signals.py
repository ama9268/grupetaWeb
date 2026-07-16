from django.db.models.signals import pre_save, post_save
from django.dispatch import Signal, receiver

from .models import Event, EventRSVP

# Se dispara cuando un miembro pasa a "Voy" en un evento/salida (ver
# update_events_attended más abajo). Sin receptores conectados todavía — punto de
# enganche preparado para la futura notificación a un grupo de Telegram cuando alguien
# se apunta a una Salida (fuera de alcance de esta iteración, ver apps/events/CLAUDE.md).
rsvp_confirmed = Signal()  # providing_args: rsvp (EventRSVP)


@receiver(post_save, sender=Event)
def create_event_chat_room(sender, instance, created, **kwargs):
    """Al crear un evento se crea automáticamente su subsala de chat (categoría 'eventos')."""
    if not created or instance.chat_room_id is not None:
        return
    from apps.chat.models import ChatRoom
    room = ChatRoom.objects.create(
        name=instance.title,
        slug=f'evento-{instance.pk}',
        category=ChatRoom.Category.EVENTOS,
        group=instance.group,
    )
    instance.chat_room = room
    instance.save(update_fields=['chat_room'])


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
    going = EventRSVP.Response.SI
    profile = instance.member.profile

    if current == going and previous != going:
        profile.total_events_attended += 1
        profile.save(update_fields=['total_events_attended'])
        rsvp_confirmed.send(sender=EventRSVP, rsvp=instance)
    elif current != going and previous == going:
        profile.total_events_attended = max(0, profile.total_events_attended - 1)
        profile.save(update_fields=['total_events_attended'])
