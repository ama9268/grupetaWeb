from django.db import models
from django.contrib.auth.models import User


class ChatRoom(models.Model):
    class Category(models.TextChoices):
        GENERAL = 'general', 'General'
        EVENTOS = 'eventos', 'Eventos'

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.GENERAL, db_index=True
    )
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return self.name


class Message(models.Model):
    room = models.ForeignKey(
        ChatRoom, on_delete=models.CASCADE, related_name='messages'
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deleted_messages'
    )

    class Meta:
        ordering = ['created_at']
        indexes = [models.Index(fields=['room', 'created_at'], name='chat_msg_room_created_idx')]

    def __str__(self):
        return f'{self.user.email}: {self.content[:50]}'
