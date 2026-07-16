from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


def approved_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'profile') or not request.user.profile.is_approved:
            return redirect('accounts:pending')
        return view_func(request, *args, **kwargs)
    return wrapper


def moderator_required(view_func):
    """Exige moderar AL MENOS una grupeta. Ver nota en `mixins.ModeratorRequiredMixin`."""
    @wraps(view_func)
    @approved_required
    def wrapper(request, *args, **kwargs):
        if not request.user.profile.is_moderator:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """Exige el rol Admin GLOBAL."""
    @wraps(view_func)
    @approved_required
    def wrapper(request, *args, **kwargs):
        if not request.user.profile.is_admin:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper
