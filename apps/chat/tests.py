import pytest
from channels.db import database_sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User
from django.urls import re_path

from .consumers import ChatConsumer
from .models import Message

# Minimal ASGI app that routes directly to the consumer (bypasses auth middleware)
test_asgi = URLRouter([re_path(r'^ws/chat/$', ChatConsumer.as_asgi())])


@database_sync_to_async
def create_chat_user():
    user = User.objects.create_user(
        username='chat@test.com',
        email='chat@test.com',
        password='testpass123',
        is_active=True,
    )
    user.profile.role = 'member'
    user.profile.status = 'approved'
    user.profile.save()
    return user


@database_sync_to_async
def create_message(user, content):
    return Message.objects.create(user=user, content=content)


@database_sync_to_async
def message_count():
    return Message.objects.count()


@pytest.fixture
def in_memory_channel_layer(settings):
    settings.CHANNEL_LAYERS = {
        'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}
    }
    from channels.layers import channel_layers
    channel_layers.backends = {}
    yield
    channel_layers.backends = {}


@pytest.mark.django_db(transaction=True)
async def test_websocket_sends_history_on_connect(in_memory_channel_layer):
    user = await create_chat_user()
    existing = await create_message(user, 'Mensaje histórico')

    communicator = WebsocketCommunicator(test_asgi, '/ws/chat/')
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

    communicator = WebsocketCommunicator(test_asgi, '/ws/chat/')
    communicator.scope['user'] = user
    connected, _ = await communicator.connect()
    assert connected

    await communicator.receive_json_from()  # consume history

    await communicator.send_json_to({'content': 'Hola desde test'})
    response = await communicator.receive_json_from()

    assert response['type'] == 'message'
    assert response['message']['content'] == 'Hola desde test'
    assert await message_count() == 1

    await communicator.disconnect()
