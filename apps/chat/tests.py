import pytest
from channels.db import database_sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User
from django.urls import re_path, reverse

from .consumers import ChatConsumer
from .models import ChatRoom, Message

# ASGI mínimo que enruta directamente al consumer (salta el middleware de auth).
test_asgi = URLRouter([
    re_path(r'^ws/chat/(?P<slug>[-\w]+)/$', ChatConsumer.as_asgi()),
])


@database_sync_to_async
def create_chat_user():
    user = User.objects.create_user(
        username='chat@test.com', email='chat@test.com',
        password='testpass123', is_active=True,
    )
    user.profile.role = 'member'
    user.profile.status = 'approved'
    user.profile.save()
    return user


@database_sync_to_async
def create_pending_user():
    user = User.objects.create_user(
        username='pending@test.com', email='pending@test.com',
        password='testpass123', is_active=True,
    )
    user.profile.role = 'member'
    user.profile.status = 'pending'
    user.profile.save()
    return user


@database_sync_to_async
def create_room(slug='general', name='General', archived=False):
    # La migración de datos ya siembra la sala 'general'; reutilizarla si existe.
    room, _ = ChatRoom.objects.get_or_create(
        slug=slug, defaults={'name': name, 'is_archived': archived}
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
    near = Event.objects.create(title='Cercano', start_at=now + timedelta(days=2), created_by=approved_moderator)
    far = Event.objects.create(title='Lejano', start_at=now + timedelta(days=20), created_by=approved_moderator)
    cancelado = Event.objects.create(title='Cancelado', start_at=now + timedelta(days=3), created_by=approved_moderator)
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
    room = ChatRoom.objects.create(slug='sala-test', name='Test')
    msg = Message.objects.create(room=room, user=approved_member, content='hola')
    response = member_client.post(reverse('chat:delete_message', args=[msg.pk]))
    assert response.status_code == 302
    msg.refresh_from_db()
    assert msg.is_deleted is True


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
