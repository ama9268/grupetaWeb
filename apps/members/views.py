from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, DetailView, UpdateView
from django.urls import reverse_lazy

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
    template_name = 'members/profile_edit.html'
    form_class = ProfileEditForm
    success_url = reverse_lazy('members:list')

    def get_object(self, queryset=None):
        return self.request.user.profile

    def form_valid(self, form):
        messages.success(self.request, 'Perfil actualizado correctamente.')
        return super().form_valid(form)
