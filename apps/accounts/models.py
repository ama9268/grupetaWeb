from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('moderator', 'Moderador'),
        ('member', 'Miembro'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    # Campos de perfil ciclista
    photo = models.ImageField(upload_to='profiles/', blank=True, null=True)
    bio = models.TextField(blank=True)
    bikes = models.TextField(blank=True, help_text='Lista de bicicletas (una por línea)')
    total_km = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_routes = models.IntegerField(default=0)
    total_events_attended = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return f'{self.user.email} ({self.get_role_display()} / {self.get_status_display()})'

    @property
    def is_approved(self):
        return self.status == 'approved'

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_moderator(self):
        return self.role in ('admin', 'moderator')
