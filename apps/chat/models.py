from django.db import models
from django.contrib.auth.models import User


class Message(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deleted_messages'
    )

    class Meta:
        ordering = ['created_at']
        indexes = [models.Index(fields=['created_at'])]

    def __str__(self):
        return f'{self.user.email}: {self.content[:50]}'
