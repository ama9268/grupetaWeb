from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.views.decorators.http import require_POST
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.shortcuts import get_object_or_404, redirect

from apps.accounts.mixins import ApprovedUserMixin
from apps.media_gallery.cloudinary_utils import (
    upload_image, upload_video, delete_asset,
)
from .models import ChatRoom, Message
from .forms import ChatAttachmentForm
from .serializers import serialize_message

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


def _broadcast_message(room_slug, message):
    """Difunde un mensaje nuevo a la sala. Mismo evento que emite el consumer WS."""
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    try:
        async_to_sync(channel_layer.group_send)(
            f'chat_{room_slug}',
            {'type': 'chat_message', 'message': message},
        )
    except Exception:
        pass


@login_required
@require_POST
def upload_attachment(request, slug):
    """Sube un adjunto (imagen/vídeo) del chat a Cloudinary y publica el mensaje.

    El binario viaja por HTTP (no por el WebSocket); una vez subido, se crea el
    Message y se difunde por el channel layer, así que llega a todos los clientes
    —incluido el que sube— como un mensaje normal.
    """
    profile = getattr(request.user, 'profile', None)
    if profile is None or profile.status != 'approved':
        raise PermissionDenied

    room = get_object_or_404(ChatRoom, slug=slug)
    if room.is_archived:
        return JsonResponse(
            {'error': 'Esta sala está archivada (solo lectura).'}, status=403
        )

    form = ChatAttachmentForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({'error': form.errors.get('__all__', ['Archivo no válido'])[0]}, status=400)

    media_type = form.cleaned_data['media_type']
    file = form.cleaned_data['file']
    try:
        if media_type == 'image':
            public_id, url = upload_image(file)
        else:
            public_id, url = upload_video(file)
    except Exception:
        return JsonResponse({'error': 'No se pudo subir el archivo. Inténtalo de nuevo.'}, status=502)

    msg = Message.objects.create(
        room=room,
        user=request.user,
        content=form.cleaned_data.get('caption', '').strip(),
        attachment_type=media_type,
        attachment_url=url,
        attachment_public_id=public_id,
    )
    _broadcast_message(room.slug, serialize_message(msg))
    return JsonResponse({'ok': True})


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


@login_required
def delete_message(request, message_id):
    msg = get_object_or_404(Message, pk=message_id)
    if request.method != 'POST':
        return redirect('chat:room_detail', slug=msg.room.slug)
    if msg.user != request.user and request.user.profile.role not in ('admin', 'moderator'):
        raise PermissionDenied
    msg.is_deleted = True
    msg.deleted_by = request.user
    msg.save(update_fields=['is_deleted', 'deleted_by'])
    # Si el mensaje tenía un adjunto, se elimina también de Cloudinary (best-effort).
    if msg.attachment_public_id:
        resource_type = 'video' if msg.attachment_type == 'video' else 'image'
        delete_asset(msg.attachment_public_id, resource_type=resource_type)
    _broadcast_delete(msg.room.slug, msg.pk)
    return redirect('chat:room_detail', slug=msg.room.slug)
