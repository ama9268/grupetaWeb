from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView

from apps.groups.models import Group, Membership
from apps.groups.permissions import require_group_moderator
from apps.groups.services import approve_membership, reject_membership
from .mixins import ModeratorRequiredMixin


class PendingApprovalView(TemplateView):
    template_name = 'accounts/pending_approval.html'


class ManageUsersView(ModeratorRequiredMixin, TemplateView):
    template_name = 'accounts/manage_users.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = self.request.user.profile
        groups = Group.objects.active() if profile.is_admin else profile.moderated_groups()

        sections = []
        for group in groups.order_by('name'):
            pending = (
                Membership.objects.filter(group=group, status=Membership.Status.PENDING)
                .select_related('user')
                .order_by('created_at')
            )
            approved = (
                Membership.objects.filter(group=group, status=Membership.Status.APPROVED)
                .select_related('user', 'user__profile')
                .order_by('user__username')
            )
            sections.append({'group': group, 'pending': pending, 'approved': approved})
        ctx['sections'] = sections
        return ctx


def approve_user(request, membership_id):
    if request.method != 'POST':
        return redirect('accounts:manage_users')

    membership = get_object_or_404(
        Membership.objects.select_related('group', 'user'),
        pk=membership_id, status=Membership.Status.PENDING,
    )
    require_group_moderator(request.user, membership.group)
    approve_membership(membership, decided_by=request.user)

    if request.headers.get('HX-Request'):
        return HttpResponse('')
    messages.success(request, f'{membership.user.username} aprobado en {membership.group.name}.')
    return redirect('accounts:manage_users')


def reject_user(request, membership_id):
    if request.method != 'POST':
        return redirect('accounts:manage_users')

    membership = get_object_or_404(
        Membership.objects.select_related('group', 'user'),
        pk=membership_id, status=Membership.Status.PENDING,
    )
    require_group_moderator(request.user, membership.group)
    reject_membership(membership, decided_by=request.user)

    if request.headers.get('HX-Request'):
        return HttpResponse('')
    messages.warning(request, f'{membership.user.username} rechazado en {membership.group.name}.')
    return redirect('accounts:manage_users')


def change_role(request, membership_id):
    if request.method != 'POST':
        return redirect('accounts:manage_users')

    membership = get_object_or_404(
        Membership.objects.select_related('group', 'user'),
        pk=membership_id, status=Membership.Status.APPROVED,
    )
    require_group_moderator(request.user, membership.group)

    new_role = request.POST.get('role', '')
    if new_role not in (Membership.Role.MEMBER, Membership.Role.MODERATOR):
        return redirect('accounts:manage_users')

    # Guarda: no dejar una grupeta sin ningún moderador aprobado.
    degrading_last_moderator = (
        membership.role == Membership.Role.MODERATOR
        and new_role != Membership.Role.MODERATOR
        and Membership.objects.filter(
            group=membership.group,
            role=Membership.Role.MODERATOR,
            status=Membership.Status.APPROVED,
        ).count() <= 1
    )
    if degrading_last_moderator:
        messages.error(
            request,
            'No puedes quitar el último moderador aprobado de esta grupeta.',
        )
        if request.headers.get('HX-Request'):
            # Recargar para revertir el <select> y mostrar el error.
            resp = HttpResponse(status=204)
            resp['HX-Refresh'] = 'true'
            return resp
        return redirect('accounts:manage_users')

    membership.role = new_role
    membership.save(update_fields=['role'])

    if request.headers.get('HX-Request'):
        return HttpResponse('')
    messages.success(request, f'Rol de {membership.user.username} en {membership.group.name} actualizado.')
    return redirect('accounts:manage_users')
