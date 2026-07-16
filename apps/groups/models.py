from django.contrib.auth.models import User
from django.db import models


class GroupQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class Group(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='groups/logos/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_groups'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = GroupQuerySet.as_manager()

    class Meta:
        ordering = ['name']
        indexes = [models.Index(fields=['is_active'])]

    def __str__(self):
        return self.name


class Membership(models.Model):
    class Role(models.TextChoices):
        MODERATOR = 'moderator', 'Moderador'
        MEMBER = 'member', 'Miembro'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendiente'
        APPROVED = 'approved', 'Aprobado'
        REJECTED = 'rejected', 'Rechazado'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='decided_memberships'
    )

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'group'], name='unique_membership_per_user_group')
        ]
        indexes = [
            models.Index(fields=['group', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['group', 'role', 'status']),
        ]

    def __str__(self):
        return f'{self.user} @ {self.group} ({self.get_role_display()} / {self.get_status_display()})'
