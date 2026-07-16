from django.db import models
from django.contrib.auth.models import User

from apps.groups.querysets import GroupScopedQuerySet
from .sanitize import sanitize_html


class Post(models.Model):
    objects = GroupScopedQuerySet.as_manager()

    group = models.ForeignKey(
        'groups.Group', on_delete=models.PROTECT, related_name='posts'
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    header_image = models.ImageField(upload_to='blog/', blank=True, null=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['group', '-created_at'], name='blog_post_group_created_idx'),
        ]

    def save(self, *args, **kwargs):
        # El contenido se muestra con |safe: sanear el HTML antes de persistirlo (anti-XSS).
        self.content = sanitize_html(self.content)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def likes_count(self):
        return self.likes.count()


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


class Like(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('post', 'user')]
