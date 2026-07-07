from django import forms
from .models import Route
from .services import validate_gpx_upload


class RouteForm(forms.ModelForm):
    class Meta:
        model = Route
        fields = ('title', 'description', 'gpx_file')
        labels = {
            'title': 'Título de la ruta',
            'description': 'Descripción',
            'gpx_file': 'Archivo GPX',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_gpx_file(self):
        return validate_gpx_upload(self.cleaned_data['gpx_file'])
