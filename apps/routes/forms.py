from django import forms

from .models import Route
from .services import validate_gpx_upload


CHECKBOX_FIELDS = {'recommendable_for_salidas', 'is_archived'}


class RouteForm(forms.ModelForm):
    class Meta:
        model = Route
        fields = ('group', 'title', 'description', 'difficulty', 'recommendable_for_salidas', 'gpx_file')
        labels = {
            'group': 'Grupeta',
            'title': 'Título de la ruta',
            'description': 'Descripción',
            'difficulty': 'Nivel de dificultad',
            'gpx_file': 'Archivo GPX',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'gpx_file': forms.ClearableFileInput(attrs={'accept': '.gpx'}),
        }

    def __init__(self, *args, user=None, initial_group=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['gpx_file'].required = True
        self.fields['difficulty'].required = False
        if user is not None:
            self.fields['group'].queryset = user.profile.moderated_groups().order_by('name')
            if initial_group is not None:
                self.initial.setdefault('group', initial_group.pk)
        # La clase `input` aplica a texto/select; el input de archivo y la
        # casilla se estilizan aparte (mismo criterio que EventForm).
        for name, field in self.fields.items():
            if name == 'gpx_file' or name in CHECKBOX_FIELDS:
                continue
            css = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (css + ' input').strip()

    def clean_gpx_file(self):
        return validate_gpx_upload(self.cleaned_data['gpx_file'])


class RouteEditForm(forms.ModelForm):
    """Edición de una ruta ya existente: solo metadatos (título, descripción,
    dificultad, recomendable para Salidas, archivada). La grupeta y el trazado
    GPX no se tocan tras crear la ruta (mismo criterio que `EventForm` con
    `group` en edición). `is_archived` también se puede marcar aquí de forma
    proactiva (p.ej. un tramo cortado), no solo como consecuencia de un
    intento de borrado bloqueado (`views.route_delete`)."""

    class Meta:
        model = Route
        fields = ('title', 'description', 'difficulty', 'recommendable_for_salidas', 'is_archived')
        labels = {
            'title': 'Título de la ruta',
            'description': 'Descripción',
            'difficulty': 'Nivel de dificultad',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['difficulty'].required = False
        for name, field in self.fields.items():
            if name in CHECKBOX_FIELDS:
                continue
            css = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (css + ' input').strip()
