from django import forms
from apps.accounts.models import UserProfile


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('photo', 'bio', 'bikes')
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
            'bikes': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'photo': 'Foto de perfil',
            'bio': 'Sobre mí',
            'bikes': 'Mis bicicletas (una por línea)',
        }
