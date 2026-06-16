from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView, ListView

from django.contrib.auth.models import User
from .mixins import ModeratorRequiredMixin
from .models import UserProfile
from .emails import send_account_approved_email


class PendingApprovalView(TemplateView):
    template_name = 'accounts/pending_approval.html'


class ManageUsersView(ModeratorRequiredMixin, ListView):
    template_name = 'accounts/manage_users.html'
    context_object_name = 'pending_users'

    def get_queryset(self):
        return User.objects.filter(
            profile__status='pending',
            is_active=False,
        ).select_related('profile').order_by('date_joined')


def approve_user(request, user_id):
    if request.method != 'POST':
        return redirect('accounts:manage_users')
    if not request.user.is_authenticated or request.user.profile.role not in ('admin', 'moderator'):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    user = get_object_or_404(User, pk=user_id, is_active=False)
    user.is_active = True
    user.save()
    user.profile.status = 'approved'
    user.profile.save()
    send_account_approved_email(user)
    messages.success(request, f'Usuario {user.email} aprobado correctamente.')
    return redirect('accounts:manage_users')


def reject_user(request, user_id):
    if request.method != 'POST':
        return redirect('accounts:manage_users')
    if not request.user.is_authenticated or request.user.profile.role not in ('admin', 'moderator'):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    user = get_object_or_404(User, pk=user_id, is_active=False)
    user.profile.status = 'rejected'
    user.profile.save()
    messages.warning(request, f'Usuario {user.email} rechazado.')
    return redirect('accounts:manage_users')
