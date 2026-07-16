from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Group, Membership


@receiver(post_save, sender=Membership)
def notify_pending_membership(sender, instance, created, **kwargs):
    """Avisa a los moderadores de ESA grupeta (+ Admins globales) de una solicitud nueva."""
    if created and instance.status == Membership.Status.PENDING:
        from apps.accounts.emails import send_approval_request_email
        send_approval_request_email(instance)


@receiver(post_save, sender=Group)
def create_default_chat_room(sender, instance, created, **kwargs):
    """Toda grupeta nueva nace con su sala de chat «General» (mismo patrón que
    `apps.events.signals.create_event_chat_room` para la subsala de un evento)."""
    if not created:
        return
    from apps.chat.models import ChatRoom
    ChatRoom.objects.create(
        name='General',
        slug=f'{instance.slug}-general',
        category=ChatRoom.Category.GENERAL,
        group=instance,
    )
