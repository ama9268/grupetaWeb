from allauth.account.models import EmailAddress
from django import forms
from django.contrib.auth.models import User

from apps.accounts.models import UserProfile
from apps.accounts.validators import USERNAME_MAX_LENGTH, username_validators


class ProfileEditForm(forms.ModelForm):
    """Formulario combinado de cuenta (`User`) + perfil (`UserProfile`).

    Edita username, nombre, apellidos, email (datos de cuenta) y foto, bio,
    bicis (perfil). `role` y `status` NO forman parte de los campos: son de solo
    lectura y se gestionan en `accounts`. El formulario opera sobre un `User`
    (la vista pasa el usuario objetivo como `instance`).
    """

    username = forms.CharField(
        label='Nombre de usuario',
        max_length=USERNAME_MAX_LENGTH,
        validators=username_validators,
        help_text='Tu identificador público. Letras, dígitos y . _ - (3–30).',
    )
    photo = forms.ImageField(label='Foto de perfil', required=False)
    bio = forms.CharField(
        label='Sobre mí',
        required=False,
        widget=forms.Textarea(attrs={'rows': 4}),
    )
    bikes = forms.CharField(
        label='Mis bicicletas (una por línea)',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')
        labels = {
            'first_name': 'Nombre',
            'last_name': 'Apellidos',
            'email': 'Email',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True
        # Inicializar los campos de perfil desde el UserProfile asociado.
        profile = getattr(self.instance, 'profile', None)
        if profile is not None:
            self.fields['bio'].initial = profile.bio
            self.fields['bikes'].initial = profile.bikes
        # Aplicar las clases del sistema de diseño (static/css/main.css).
        for name in ('username', 'first_name', 'last_name', 'email'):
            self.fields[name].widget.attrs.setdefault('class', 'input')
        for name in ('bio', 'bikes'):
            self.fields[name].widget.attrs.update(
                {'class': 'input', 'style': 'height:auto;resize:vertical;'}
            )

    def clean_username(self):
        username = self.cleaned_data['username']
        exists = (
            User.objects.exclude(pk=self.instance.pk)
            .filter(username__iexact=username)
            .exists()
        )
        if exists:
            raise forms.ValidationError('Ese nombre de usuario ya está en uso.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        exists = (
            User.objects.exclude(pk=self.instance.pk)
            .filter(email__iexact=email)
            .exists()
        )
        if exists:
            raise forms.ValidationError('Ese email ya está en uso.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        email_changed = 'email' in self.changed_data
        if commit:
            user.save()
            self._save_profile(user)
            if email_changed:
                self._sync_allauth_email(user)
        return user

    def _save_profile(self, user):
        profile = user.profile
        # La foto solo se reemplaza si se ha subido una nueva (no borrar la actual).
        photo = self.cleaned_data.get('photo')
        if photo is not None:
            profile.photo = photo
        profile.bio = self.cleaned_data.get('bio', '')
        profile.bikes = self.cleaned_data.get('bikes', '')
        profile.save()

    def _sync_allauth_email(self, user):
        """Mantener coherente el `EmailAddress` de allauth (credencial de login)."""
        # Cualquier otra dirección deja de ser la primaria.
        EmailAddress.objects.filter(user=user).exclude(
            email__iexact=user.email
        ).update(primary=False)
        ea = EmailAddress.objects.filter(user=user, email__iexact=user.email).first()
        if ea is None:
            EmailAddress.objects.create(
                user=user, email=user.email, primary=True, verified=True,
            )
        else:
            ea.email = user.email
            ea.primary = True
            ea.verified = True
            ea.save(update_fields=['email', 'primary', 'verified'])
