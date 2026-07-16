from django import forms

from .models import Route
from .services import validate_gpx_upload


class RouteForm(forms.ModelForm):
    class Meta:
        model = Route
        fields = ('group', 'title', 'description', 'gpx_file')
        labels = {
            'group': 'Grupeta',
            'title': 'Título de la ruta',
            'description': 'Descripción',
            'gpx_file': 'Archivo GPX',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'gpx_file': forms.ClearableFileInput(attrs={'accept': '.gpx'}),
        }

    def __init__(self, *args, user=None, initial_group=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['gpx_file'].required = True
        if user is not None:
            self.fields['group'].queryset = user.profile.moderated_groups().order_by('name')
            if initial_group is not None:
                self.initial.setdefault('group', initial_group.pk)
        # La clase `input` aplica a texto/select; el input de archivo se
        # estiliza aparte (mismo criterio que EventForm).
        for name, field in self.fields.items():
            if name == 'gpx_file':
                continue
            css = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (css + ' input').strip()

    def clean_gpx_file(self):
        return validate_gpx_upload(self.cleaned_data['gpx_file'])
