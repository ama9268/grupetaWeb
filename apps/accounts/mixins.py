from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


class ApprovedUserMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not hasattr(request.user, 'profile') or not request.user.profile.is_approved:
            return redirect('accounts:pending')
        return super().dispatch(request, *args, **kwargs)


class ModeratorRequiredMixin(ApprovedUserMixin):
    """Exige moderar AL MENOS una grupeta (gating de pantallas de creación).

    Para permisos sobre un objeto ya existente de una grupeta concreta, usar
    `apps.groups.permissions.require_group_moderator` (o el mixin de objeto
    equivalente), no este mixin.
    """

    def dispatch(self, request, *args, **kwargs):
        if (
            request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile.is_approved
            and not request.user.profile.is_moderator
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class AdminRequiredMixin(ApprovedUserMixin):
    """Exige el rol Admin GLOBAL (no confundir con moderador de una grupeta)."""

    def dispatch(self, request, *args, **kwargs):
        if (
            request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile.is_approved
            and not request.user.profile.is_admin
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
