import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from .models import ChatRoom, Message
from .serializers import serialize_message

HISTORY_LIMIT = 100
PAGE_SIZE = 50


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        if not self.scope['user'].is_authenticated:
            await self.close()
            return

        self.slug = self.scope['url_route']['kwargs']['slug']
        self.room = await self.get_room(self.slug)
        if self.room is None:
            await self.close()
            return

        # Coherente con ApprovedUserMixin de las vistas HTTP, pero acotado a la
        # grupeta de ESTA sala (no basta con estar aprobado en cualquier otra).
        if not await self.is_group_member():
            await self.close()
            return

        self.group_name = f'chat_{self.slug}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        history, has_more = await self.get_history()
        await self.send(text_data=json.dumps({
            'type': 'history',
            'messages': history,
            'has_more': has_more,
            'archived': self.room.is_archived,
        }))

    async def disconnect(self, close_code):
        if getattr(self, 'group_name', None):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        if data.get('type') == 'load_more':
            before_id = data.get('before_id')
            if not before_id:
                return
            older, has_more = await self.get_older_messages(int(before_id))
            await self.send(text_data=json.dumps({
                'type': 'older_messages',
                'messages': older,
                'has_more': has_more,
            }))
            return

        content = (data.get('content') or '').strip()
        if not content:
            return

        # Las salas archivadas (evento cancelado/borrado) son de solo lectura.
        if await self.is_room_archived():
            await self.send(text_data=json.dumps({
                'type': 'error',
                'detail': 'Esta sala está archivada (solo lectura).',
            }))
            return

        message = await self.save_message(content)
        await self.channel_layer.group_send(
            self.group_name,
            {'type': 'chat_message', 'message': message},
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({'type': 'message', 'message': event['message']}))

    async def chat_delete(self, event):
        await self.send(text_data=json.dumps({'type': 'deleted', 'id': event['id']}))

    @database_sync_to_async
    def is_group_member(self):
        user = self.scope['user']
        profile = getattr(user, 'profile', None)
        return bool(profile) and profile.is_member_of(self.room.group)

    @database_sync_to_async
    def get_room(self, slug):
        return ChatRoom.objects.select_related('group').filter(slug=slug).first()

    @database_sync_to_async
    def is_room_archived(self):
        # Se re-consulta para reflejar un archivado ocurrido tras la conexión.
        return ChatRoom.objects.filter(pk=self.room.pk, is_archived=True).exists()

    @database_sync_to_async
    def save_message(self, content):
        msg = Message.objects.create(
            user=self.scope['user'], content=content, room=self.room
        )
        return serialize_message(msg)

    @database_sync_to_async
    def get_history(self):
        qs = list(
            Message.objects.filter(room=self.room, is_deleted=False)
            .select_related('user')
            .order_by('-created_at')[:HISTORY_LIMIT + 1]
        )
        has_more = len(qs) > HISTORY_LIMIT
        qs = qs[:HISTORY_LIMIT]
        qs.reverse()
        return [serialize_message(m) for m in qs], has_more

    @database_sync_to_async
    def get_older_messages(self, before_id):
        qs = list(
            Message.objects.filter(room=self.room, is_deleted=False, pk__lt=before_id)
            .select_related('user')
            .order_by('-created_at')[:PAGE_SIZE + 1]
        )
        has_more = len(qs) > PAGE_SIZE
        qs = qs[:PAGE_SIZE]
        qs.reverse()
        return [serialize_message(m) for m in qs], has_more
