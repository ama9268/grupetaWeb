from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


class ApprovedUserMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not hasattr(request.user, 'profile') or request.user.profile.status != 'approved':
            return redirect('accounts:pending')
        return super().dispatch(request, *args, **kwargs)


class RoleRequiredMixin(ApprovedUserMixin):
    required_roles = []

    def dispatch(self, request, *args, **kwargs):
        # Comprobar el rol ANTES de ejecutar la vista, para no aplicar efectos
        # secundarios (crear/editar) a usuarios sin permiso. Solo se comprueba
        # cuando el usuario está autenticado y aprobado; el resto de casos
        # (login/aprobación) los resuelve ApprovedUserMixin en super().dispatch.
        if (
            request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile.status == 'approved'
            and request.user.profile.role not in self.required_roles
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class ModeratorRequiredMixin(RoleRequiredMixin):
    required_roles = ['admin', 'moderator']


class AdminRequiredMixin(RoleRequiredMixin):
    required_roles = ['admin']
