from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, DetailView, UpdateView
from django.urls import reverse

from apps.accounts.mixins import ApprovedUserMixin
from apps.accounts.models import UserProfile
from .forms import ProfileEditForm


class MemberListView(ApprovedUserMixin, ListView):
    template_name = 'members/member_list.html'
    context_object_name = 'members'

    def get_queryset(self):
        return UserProfile.objects.filter(
            status='approved',
        ).select_related('user').order_by('-total_km')


class MemberDetailView(ApprovedUserMixin, DetailView):
    template_name = 'members/member_detail.html'
    context_object_name = 'member_profile'

    def get_queryset(self):
        return UserProfile.objects.filter(status='approved').select_related('user')


class ProfileEditView(ApprovedUserMixin, UpdateView):
    """Edición del perfil + cuenta.

    Sin `pk` en la URL se edita el propio usuario. Con `pk` (de `UserProfile`,
    coherente con `members:detail`) se edita a otro miembro: reservado a
    admin/moderador. El formulario opera sobre el `User` objetivo.
    """
    template_name = 'members/profile_edit.html'
    form_class = ProfileEditForm

    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk')
        if pk is None:
            return self.request.user
        # Editar a otro miembro: solo admin/moderador.
        if not self.request.user.profile.is_moderator:
            raise PermissionDenied
        target = get_object_or_404(
            UserProfile.objects.select_related('user'), pk=pk
        )
        return target.user

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
