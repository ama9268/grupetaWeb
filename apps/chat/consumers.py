import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from .models import Message

HISTORY_LIMIT = 100
PAGE_SIZE = 50


class ChatConsumer(AsyncWebsocketConsumer):
    ROOM_GROUP = 'chat_general'

    async def connect(self):
        if not self.scope['user'].is_authenticated:
            await self.close()
            return

        await self.channel_layer.group_add(self.ROOM_GROUP, self.channel_name)
        await self.accept()

        history, has_more = await self.get_history()
        await self.send(text_data=json.dumps({
            'type': 'history',
            'messages': history,
            'has_more': has_more,
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.ROOM_GROUP, self.channel_name)

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

        message = await self.save_message(content)
        await self.channel_layer.group_send(
            self.ROOM_GROUP,
            {'type': 'chat_message', 'message': message},
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({'type': 'message', 'message': event['message']}))

    @database_sync_to_async
    def save_message(self, content):
        msg = Message.objects.create(user=self.scope['user'], content=content)
        return self._serialize(msg)

    @database_sync_to_async
    def get_history(self):
        qs = list(
            Message.objects.filter(is_deleted=False)
            .select_related('user')
            .order_by('-created_at')[:HISTORY_LIMIT + 1]
        )
        has_more = len(qs) > HISTORY_LIMIT
        qs = qs[:HISTORY_LIMIT]
        qs.reverse()
        return [self._serialize(m) for m in qs], has_more

    @database_sync_to_async
    def get_older_messages(self, before_id):
        qs = list(
            Message.objects.filter(is_deleted=False, pk__lt=before_id)
            .select_related('user')
            .order_by('-created_at')[:PAGE_SIZE + 1]
        )
        has_more = len(qs) > PAGE_SIZE
        qs = qs[:PAGE_SIZE]
        qs.reverse()
        return [self._serialize(m) for m in qs], has_more

    def _serialize(self, msg):
        return {
            'id': msg.pk,
            'user': msg.user.get_full_name() or msg.user.email,
            'content': msg.content,
            'timestamp': msg.created_at.strftime('%d/%m/%Y %H:%M'),
        }
