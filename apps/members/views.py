from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, DetailView, UpdateView
from django.urls import reverse

from apps.accounts.mixins import ApprovedUserMixin
from apps.accounts.models import UserProfile
from apps.groups.mixins import ActiveGroupMixin
from apps.groups.models import Membership
from .forms import ProfileEditForm


class MemberListView(ApprovedUserMixin, ActiveGroupMixin, ListView):
    template_name = 'members/member_list.html'
    context_object_name = 'members'

    def get_queryset(self):
        return UserProfile.objects.filter(
            user__memberships__group=self.active_group,
            user__memberships__status=Membership.Status.APPROVED,
        ).select_related('user').order_by('-total_km')


class MemberDetailView(ApprovedUserMixin, DetailView):
    template_name = 'members/member_detail.html'
    context_object_name = 'member_profile'

    def get_queryset(self):
        # Acceso por enlace directo: cualquier grupeta que comparta con el
        # usuario (no solo la "activa"), igual que en events/blog/chat.
        return UserProfile.objects.filter(
            user__memberships__group__in=self.request.user.profile.approved_groups(),
            user__memberships__status=Membership.Status.APPROVED,
        ).select_related('user').distinct()


class ProfileEditView(ApprovedUserMixin, UpdateView):
    """Edición del perfil + cuenta.

    Sin `pk` en la URL se edita el propio usuario. Con `pk` (de `UserProfile`,
    coherente con `members:detail`) se edita a otro miembro: reservado a
    admin global o a un moderador que comparta con él una grupeta que modera.
    El formulario opera sobre el `User` objetivo.
    """
    template_name = 'members/profile_edit.html'
    form_class = ProfileEditForm

    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk')
        if pk is None:
            return self.request.user
        target = get_object_or_404(
            UserProfile.objects.select_related('user'), pk=pk
        )
        if not self._can_edit(target.user):
            raise PermissionDenied
        return target.user

    def _can_edit(self, target_user):
        profile = self.request.user.profile
        if profile.is_admin:
            return True
        target_groups = Membership.objects.filter(
            user=target_user, status=Membership.Status.APPROVED,
        ).values_list('group_id', flat=True)
        return profile.moderated_groups().filter(pk__in=target_groups).exists()

    @property
    def is_self(self):
        return self.object == self.request.user

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['is_self'] = self.is_self
        ctx['target_profile'] = self.object.profile
        return ctx

    def get_success_url(self):
        return reverse('members:detail', args=[self.object.profile.pk])

    def form_valid(self, form):
        messages.success(self.request, 'Perfil actualizado correctamente.')
        return super().form_valid(form)
