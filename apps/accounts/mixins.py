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
        result = super().dispatch(request, *args, **kwargs)
        if hasattr(result, 'status_code') and result.status_code in (302, 403):
            return result
        if request.user.profile.role not in self.required_roles:
            raise PermissionDenied
        return result


class ModeratorRequiredMixin(RoleRequiredMixin):
    required_roles = ['admin', 'moderator']


class AdminRequiredMixin(RoleRequiredMixin):
    required_roles = ['admin']
