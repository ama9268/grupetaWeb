from django.db import models
from django.contrib.auth.models import User


class UserProfileQuerySet(models.QuerySet):
    def approved(self):
        from apps.groups.models import Membership
        return self.filter(
            models.Q(is_admin=True)
            | models.Q(user__memberships__status=Membership.Status.APPROVED)
        ).distinct()


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    # Rol GLOBAL: ve y gestiona todas las grupetas, como si perteneciera a todas.
    # El rol Moderador, en cambio, es por grupeta (ver apps.groups.Membership).
    is_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # Campos de perfil ciclista
    photo = models.ImageField(upload_to='profiles/', blank=True, null=True)
    bio = models.TextField(blank=True)
    bikes = models.TextField(blank=True, help_text='Lista de bicicletas (una por línea)')
    total_km = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_routes = models.IntegerField(default=0)
    total_events_attended = models.IntegerField(default=0)

    objects = UserProfileQuerySet.as_manager()

    class Meta:
        indexes = [
            models.Index(fields=['is_admin'], name='accounts_up_is_admin_idx'),
        ]

    def __str__(self):
        # Identificador público = username (el email es dato privado).
        identifier = self.user.username or self.user.email
        return f'{identifier} ({self.role_label})'

    @property
    def is_approved(self):
        """¿Tiene acceso a la plataforma? Admin global, o al menos una Membership aprobada."""
        if self.is_admin:
            return True
        from apps.groups.models import Membership
        return Membership.objects.filter(user=self.user, status=Membership.Status.APPROVED).exists()

    def approved_groups(self):
        """Grupetas donde el usuario es miembro aprobado (todas, si es Admin global)."""
        from apps.groups.models import Group, Membership
        if self.is_admin:
            return Group.objects.active()
        return Group.objects.filter(
            memberships__user=self.user,
            memberships__status=Membership.Status.APPROVED,
            is_active=True,
        ).distinct()

    def moderated_groups(self):
        """Grupetas donde el usuario es moderador aprobado (todas, si es Admin global)."""
        from apps.groups.models import Group, Membership
        if self.is_admin:
            return Group.objects.active()
        return Group.objects.filter(
            memberships__user=self.user,
            memberships__status=Membership.Status.APPROVED,
            memberships__role=Membership.Role.MODERATOR,
            is_active=True,
        ).distinct()

    def is_group_moderator(self, group):
        return self.is_admin or self.moderated_groups().filter(pk=group.pk).exists()

    def is_member_of(self, group):
        return self.is_admin or self.approved_groups().filter(pk=group.pk).exists()

    @property
    def is_moderator(self):
        """¿Modera AL MENOS una grupeta? Para dar acceso a pantallas de creación
        (p.ej. "nuevo evento"). Para permisos sobre un objeto ya existente de una
        grupeta concreta, usar `is_group_moderator(group)`."""
        return self.is_admin or self.moderated_groups().exists()

    @property
    def role_label(self):
        """Etiqueta de rol para mostrar en la UI (badges de directorio/perfil)."""
        if self.is_admin:
            return 'Admin'
        if self.is_moderator:
            return 'Moderador'
        return 'Miembro'
