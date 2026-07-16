import pytest
from channels.db import database_sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User
from django.urls import re_path, reverse

from apps.groups.constants import DEFAULT_GROUP_NAME, DEFAULT_GROUP_SLUG
from apps.groups.models import Group, Membership
from .consumers import ChatConsumer
from .models import ChatRoom, Message

# ASGI mínimo que enruta directamente al consumer (salta el middleware de auth).
test_asgi = URLRouter([
    re_path(r'^ws/chat/(?P<slug>[-\w]+)/$', ChatConsumer.as_asgi()),
])


def _default_group():
    group, _ = Group.objects.get_or_create(slug=DEFAULT_GROUP_SLUG, defaults={'name': DEFAULT_GROUP_NAME})
    return group


@database_sync_to_async
def create_chat_user():
    group, _ = Group.objects.get_or_create(slug=DEFAULT_GROUP_SLUG, defaults={'name': DEFAULT_GROUP_NAME})
    user = User.objects.create_user(
        username='chat@test.com', email='chat@test.com',
        password='testpass123', is_active=True,
    )
    Membership.objects.create(user=user, group=group, status=Membership.Status.APPROVED)
    return user


@database_sync_to_async
def create_pending_user():
    group, _ = Group.objects.get_or_create(slug=DEFAULT_GROUP_SLUG, defaults={'name': DEFAULT_GROUP_NAME})
    user = User.objects.create_user(
        username='pending@test.com', email='pending@test.com',
        password='testpass123', is_active=True,
    )
    Membership.objects.create(user=user, group=group, status=Membership.Status.PENDING)
    return user


@database_sync_to_async
def create_room(slug='general', name='General', archived=False):
    # La migración de datos ya siembra la sala 'general'; reutilizarla si existe.
    group, _ = Group.objects.get_or_create(slug=DEFAULT_GROUP_SLUG, defaults={'name': DEFAULT_GROUP_NAME})
    room, _ = ChatRoom.objects.get_or_create(
        slug=slug, defaults={'name': name, 'is_archived': archived, 'group': group}
    )
    if room.is_archived != archived:
        room.is_archived = archived
        room.save(update_fields=['is_archived'])
    return room


@database_sync_to_async
def create_message(user, room, content):
    return Message.objects.create(user=user, room=room, content=content)


@database_sync_to_async
def message_count(room=None):
    qs = Message.objects.all()
    if room is not None:
        qs = qs.filter(room=room)
    return qs.count()


@pytest.fixture
def in_memory_channel_layer(settings):
    settings.CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}
    from channels.layers import channel_layers
    channel_layers.backends = {}
    yield
    channel_layers.backends = {}


@pytest.mark.django_db(transaction=True)
async def test_websocket_sends_history_on_connect(in_memory_channel_layer):
    user = await create_chat_user()
    room = await create_room()
    existing = await create_message(user, room, 'Mensaje histórico')

    communicator = WebsocketCommunicator(test_asgi, '/ws/chat/general/')
    communicator.scope['user'] = user
    connected, _ = await communicator.connect()
    assert connected

    data = await communicator.receive_json_from()
    assert data['type'] == 'history'
    assert any(m['id'] == existing.pk for m in data['messages'])
    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
async def test_websocket_persists_sent_message(in_memory_channel_layer):
    user = await create_chat_user()
    room = await create_room()

    communicator = WebsocketCommunicator(test_asgi, '/ws/chat/general/')
    communicator.scope['user'] = user
    connected, _ = await communicator.connect()
    assert connected
    await communicator.receive_json_from()  # consume history

    await communicator.send_json_to({'content': 'Hola desde test'})
    response = await communicator.receive_json_from()
    assert response['type'] == 'message'
    assert response['message']['content'] == 'Hola desde test'
    assert await message_count(room) == 1
    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
async def test_websocket_rejects_unapproved_user(in_memory_channel_layer):
    user = await create_pending_user()
    await create_room()
    communicator = WebsocketCommunicator(test_asgi, '/ws/chat/general/')
    communicator.scope['user'] = user
    connected, _ = await communicator.connect()
    assert connected is False


@pytest.mark.django_db(transaction=True)
async def test_websocket_unknown_room_is_rejected(in_memory_channel_layer):
    user = await create_chat_user()
    await create_room()  # 'general' existe, pero conectamos a otra
    communicator = WebsocketCommunicator(test_asgi, '/ws/chat/inexistente/')
    communicator.scope['user'] = user
    connected, _ = await communicator.connect()
    assert connected is False


@pytest.mark.django_db(transaction=True)
async def test_websocket_receives_delete_broadcast(in_memory_channel_layer):
    from channels.layers import get_channel_layer
    user = await create_chat_user()
    await create_room()
    communicator = WebsocketCommunicator(test_asgi, '/ws/chat/general/')
    communicator.scope['user'] = user
    connected, _ = await communicator.connect()
    assert connected
    await communicator.receive_json_from()  # history

    channel_layer = get_channel_layer()
    await channel_layer.group_send('chat_general', {'type': 'chat_delete', 'id': 99})
    response = await communicator.receive_json_from()
    assert response['type'] == 'deleted'
    assert response['id'] == 99
    await communicator.disconnect()


@pytest.mark.django_db
def test_chat_sidebar_splits_and_orders_event_rooms(moderator_client, approved_moderator):
    from datetime import timedelta
    from django.utils import timezone
    from apps.events.models import Event

    now = timezone.now()
    group = _default_group()
    near = Event.objects.create(title='Cercano', start_at=now + timedelta(days=2), created_by=approved_moderator, group=group)
    far = Event.objects.create(title='Lejano', start_at=now + timedelta(days=20), created_by=approved_moderator, group=group)
    cancelado = Event.objects.create(title='Cancelado', start_at=now + timedelta(days=3), created_by=approved_moderator, group=group)
    cancelado.cancel()

    response = moderator_client.get(reverse('chat:room_detail', args=['general']))
    active_slugs = [r.slug for r in response.context['event_rooms']]
    archived_slugs = [r.slug for r in response.context['archived_event_rooms']]

    # Cancelado va a archivadas; los activos ordenados por fecha desc (lejano antes que cercano).
    assert cancelado.chat_room.slug in archived_slugs
    assert cancelado.chat_room.slug not in active_slugs
    assert active_slugs.index(far.chat_room.slug) < active_slugs.index(near.chat_room.slug)


@pytest.mark.django_db
def test_delete_message_marks_deleted_and_broadcasts(member_client, approved_member, in_memory_channel_layer):
    room = ChatRoom.objects.create(slug='sala-test', name='Test', group=_default_group())
    msg = Message.objects.create(room=room, user=approved_member, content='hola')
    response = member_client.post(reverse('chat:delete_message', args=[msg.pk]))
    assert response.status_code == 302
    msg.refresh_from_db()
    assert msg.is_deleted is True


# --- Adjuntos (subida HTTP + borrado en Cloudinary) ---

# Cabecera PNG válida para que `filetype` reconozca el archivo como image/png.
PNG_BYTES = b'\x89PNG\r\n\x1a\n' + b'\x00' * 64
TXT_BYTES = b'esto no es una imagen ni un video, es texto plano' * 4


@pytest.mark.django_db
def test_upload_attachment_creates_message(member_client, approved_member, in_memory_channel_layer):
    from unittest.mock import patch
    from django.core.files.uploadedfile import SimpleUploadedFile
    room = ChatRoom.objects.create(slug='sala-adj', name='Adjuntos', group=_default_group())
    upload = SimpleUploadedFile('foto.png', PNG_BYTES, content_type='image/png')

    with patch('apps.chat.views.upload_image', return_value=('grupetaweb/x', 'https://cdn/x.webp')) as m:
        response = member_client.post(
            reverse('chat:upload_attachment', args=['sala-adj']),
            {'file': upload, 'caption': 'mira esto'},
        )

    assert response.status_code == 200
    assert m.called
    msg = Message.objects.get(room=room)
    assert msg.attachment_type == 'image'
    assert msg.attachment_url == 'https://cdn/x.webp'
    assert msg.attachment_public_id == 'grupetaweb/x'
    assert msg.content == 'mira esto'


@pytest.mark.django_db
def test_upload_rejects_non_media_file(member_client, approved_member):
    from django.core.files.uploadedfile import SimpleUploadedFile
    ChatRoom.objects.create(slug='sala-adj2', name='Adjuntos2', group=_default_group())
    bad = SimpleUploadedFile('nota.txt', TXT_BYTES, content_type='text/plain')
    response = member_client.post(
        reverse('chat:upload_attachment', args=['sala-adj2']), {'file': bad}
    )
    assert response.status_code == 400
    assert Message.objects.count() == 0


@pytest.mark.django_db
def test_upload_rejected_on_archived_room(member_client, approved_member):
    from django.core.files.uploadedfile import SimpleUploadedFile
    ChatRoom.objects.create(slug='sala-arch', name='Archivada', is_archived=True, group=_default_group())
    upload = SimpleUploadedFile('foto.png', PNG_BYTES, content_type='image/png')
    response = member_client.post(
        reverse('chat:upload_attachment', args=['sala-arch']), {'file': upload}
    )
    assert response.status_code == 403
    assert Message.objects.count() == 0


@pytest.mark.django_db
def test_delete_message_removes_cloudinary_asset(member_client, approved_member, in_memory_channel_layer):
    from unittest.mock import patch
    room = ChatRoom.objects.create(slug='sala-del', name='Del', group=_default_group())
    msg = Message.objects.create(
        room=room, user=approved_member, attachment_type='video',
        attachment_url='https://cdn/v.mp4', attachment_public_id='grupetaweb/v',
    )
    with patch('apps.chat.views.delete_asset') as m:
        response = member_client.post(reverse('chat:delete_message', args=[msg.pk]))
    assert response.status_code == 302
    m.assert_called_once_with('grupetaweb/v', resource_type='video')


# --- Gestión de salas (admin/moderador) ---

@pytest.mark.django_db
def test_manage_rooms_page_requires_moderator(member_client, moderator_client):
    # Miembro normal: prohibido.
    assert member_client.get(reverse('chat:manage_rooms')).status_code == 403
    # Moderador: acceso.
    assert moderator_client.get(reverse('chat:manage_rooms')).status_code == 200


@pytest.mark.django_db
def test_moderator_creates_room_with_unique_slug(moderator_client):
    group = _default_group()
    ChatRoom.objects.create(slug='salidas-de-finde', name='Existente', group=group)
    resp = moderator_client.post(
        reverse('chat:create_room'), {'name': 'Salidas de finde', 'group': group.pk}
    )
    assert resp.status_code == 302
    nueva = ChatRoom.objects.get(name='Salidas de finde')
    assert nueva.category == 'general'
    assert nueva.slug == 'salidas-de-finde-2'  # deduplicado


@pytest.mark.django_db
def test_member_cannot_create_room(member_client):
    resp = member_client.post(reverse('chat:create_room'), {'name': 'Prohibida'})
    assert resp.status_code == 403
    assert not ChatRoom.objects.filter(name='Prohibida').exists()


@pytest.mark.django_db
def test_rename_keeps_slug(moderator_client):
    room = ChatRoom.objects.create(slug='mi-sala', name='Nombre viejo', group=_default_group())
    resp = moderator_client.post(reverse('chat:rename_room', args=['mi-sala']), {'name': 'Nombre nuevo'})
    assert resp.status_code == 302
    room.refresh_from_db()
    assert room.name == 'Nombre nuevo'
    assert room.slug == 'mi-sala'  # el slug NO cambia


@pytest.mark.django_db
def test_toggle_archive_room(moderator_client):
    room = ChatRoom.objects.create(slug='temp', name='Temporal', group=_default_group())
    moderator_client.post(reverse('chat:toggle_archive_room', args=['temp']))
    room.refresh_from_db()
    assert room.is_archived is True
    moderator_client.post(reverse('chat:toggle_archive_room', args=['temp']))
    room.refresh_from_db()
    assert room.is_archived is False


@pytest.mark.django_db
def test_event_room_is_not_manageable_here(moderator_client):
    ChatRoom.objects.create(slug='evento-1', name='Evento', category='eventos', group=_default_group())
    assert moderator_client.post(reverse('chat:rename_room', args=['evento-1']), {'name': 'X'}).status_code == 404
    assert moderator_client.post(reverse('chat:toggle_archive_room', args=['evento-1'])).status_code == 404


@pytest.mark.django_db(transaction=True)
async def test_websocket_archived_room_is_read_only(in_memory_channel_layer):
    user = await create_chat_user()
    room = await create_room(slug='evento-1', name='Evento', archived=True)

    communicator = WebsocketCommunicator(test_asgi, '/ws/chat/evento-1/')
    communicator.scope['user'] = user
    connected, _ = await communicator.connect()
    assert connected
    await communicator.receive_json_from()  # history

    await communicator.send_json_to({'content': 'No debería guardarse'})
    response = await communicator.receive_json_from()
    assert response['type'] == 'error'
    assert await message_count(room) == 0
    await communicator.disconnect()
