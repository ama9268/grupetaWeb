from allauth.account.forms import SignupForm
from django import forms

from apps.groups.models import Group, Membership


class GroupSignupForm(SignupForm):
    group = forms.ModelChoiceField(
        queryset=Group.objects.active().order_by('name'),
        label='Grupeta a la que quieres unirte',
        empty_label=None,
    )

    def save(self, request):
        # super().save() ya crea el User (adapter.save_user -> is_active=False)
        # y dispara post_save(User) -> crea el UserProfile.
        user = super().save(request)
        Membership.objects.create(
            user=user,
            group=self.cleaned_data['group'],
            role=Membership.Role.MEMBER,
            status=Membership.Status.PENDING,
        )
        return user
