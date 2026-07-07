from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.views.generic import TemplateView
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.shortcuts import get_object_or_404, redirect

from apps.accounts.mixins import ApprovedUserMixin
from .models import ChatRoom, Message

# Estados de evento cuya subsala se considera inactiva (se pliega en el sidebar).
INACTIVE_EVENT_STATES = {'superado', 'cancelado'}


def _room_event(room):
    """Evento asociado a una sala (reverse OneToOne), o None si no existe."""
    try:
        return room.event
    except ObjectDoesNotExist:
        return None


def _broadcast_delete(room_slug, message_id):
    """Notifica el borrado a los clientes conectados a la sala (best-effort)."""
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    try:
        async_to_sync(channel_layer.group_send)(
            f'chat_{room_slug}',
            {'type': 'chat_delete', 'id': message_id},
        )
    except Exception:
        # Un fallo al difundir no debe romper el borrado; el mensaje ya está marcado en BD.
        pass


class ChatRoomView(ApprovedUserMixin, TemplateView):
    template_name = 'chat/room.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        slug = self.kwargs.get('slug', 'general')
        ctx['room'] = get_object_or_404(ChatRoom, slug=slug)
        ctx['general_rooms'] = ChatRoom.objects.filter(category=ChatRoom.Category.GENERAL)

        # Subsalas de eventos ordenadas por fecha del evento (las más recientes primero),
        # separando las activas de las archivadas (canceladas/superadas) para plegarlas.
        event_rooms = (
            ChatRoom.objects.filter(category=ChatRoom.Category.EVENTOS)
            .select_related('event')
            .order_by('-event__start_at')
        )
        active, archived = [], []
        for room in event_rooms:
            event = _room_event(room)
            if room.is_archived or (event is not None and event.state in INACTIVE_EVENT_STATES):
                archived.append(room)
            else:
                active.append(room)
        ctx['event_rooms'] = active
        ctx['archived_event_rooms'] = archived
        return ctx


def delete_message(request, message_id):
    msg = get_object_or_404(Message, pk=message_id)
    if request.method != 'POST':
        return redirect('chat:room_detail', slug=msg.room.slug)
    if msg.user != request.user and request.user.profile.role not in ('admin', 'moderator'):
        raise PermissionDenied
    msg.is_deleted = True
    msg.deleted_by = request.user
    msg.save(update_fields=['is_deleted', 'deleted_by'])
    _broadcast_delete(msg.room.slug, msg.pk)
    return redirect('chat:room_detail', slug=msg.room.slug)
