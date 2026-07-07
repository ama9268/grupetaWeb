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
    class Attachment(models.TextChoices):
        IMAGE = 'image', 'Imagen'
        VIDEO = 'video', 'Vídeo'

    room = models.ForeignKey(
        ChatRoom, on_delete=models.CASCADE, related_name='messages'
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_messages')
    # El contenido es opcional: un mensaje puede ser solo texto, solo adjunto,
    # o texto + adjunto (pie de foto).
    content = models.TextField(blank=True)
    # Adjunto en Cloudinary (imagen o vídeo). Vacío en mensajes de solo texto.
    attachment_type = models.CharField(
        max_length=10, choices=Attachment.choices, blank=True
    )
    attachment_url = models.URLField(max_length=500, blank=True)
    attachment_public_id = models.CharField(max_length=200, blank=True)
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
