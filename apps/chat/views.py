from django.views.generic import TemplateView
from apps.accounts.mixins import ApprovedUserMixin
from apps.accounts.decorators import approved_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

from .models import Message


class ChatRoomView(ApprovedUserMixin, TemplateView):
    template_name = 'chat/room.html'


def delete_message(request, message_id):
    if request.method != 'POST':
        return redirect('chat:room')
    msg = get_object_or_404(Message, pk=message_id)
    if msg.user != request.user and request.user.profile.role not in ('admin', 'moderator'):
        raise PermissionDenied
    msg.is_deleted = True
    msg.deleted_by = request.user
    msg.save()
    return redirect('chat:room')
