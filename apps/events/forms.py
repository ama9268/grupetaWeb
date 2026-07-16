import filetype
from django import forms

from apps.media_gallery.cloudinary_utils import ALLOWED_IMAGE_TYPES
from apps.routes.services import validate_gpx_upload
from .models import Event

MAGIC_BYTES_LENGTH = 261  # filetype solo necesita los primeros ~261 bytes


class EventForm(forms.ModelForm):
    image = forms.FileField(required=False, label='Imagen de cabecera')

    # Modo de ruta: sin ruta, elegir una existente o subir un GPX nuevo.
    ROUTE_MODE_CHOICES = (
        ('none', 'Sin ruta'),
        ('existing', 'Elegir una ruta existente'),
        ('new', 'Subir un GPX nuevo'),
    )
    route_mode = forms.ChoiceField(
        choices=ROUTE_MODE_CHOICES, required=False,
        widget=forms.RadioSelect, initial='none', label='Ruta',
    )
    gpx_file = forms.FileField(required=False, label='Archivo GPX')

    class Meta:
        model = Event
        fields = ('group', 'title', 'description', 'event_type', 'start_at', 'location', 'associated_route')
        widgets = {
            'start_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'description': forms.Textarea(attrs={'rows': 4}),
        }
        labels = {
            'group': 'Grupeta',
            'title': 'Título del evento',
            'description': 'Descripción',
            'event_type': 'Tipo de evento',
            'start_at': 'Fecha y hora',
            'location': 'Lugar',
            'associated_route': 'Ruta asociada',
        }

    def __init__(self, *args, user=None, initial_group=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['start_at'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['associated_route'].required = False

        if self.instance and self.instance.pk:
            # La grupeta de un evento ya creado no se cambia (chat/álbum/RSVP
            # ya están ligados a ella): se muestra de solo lectura.
            self.fields['group'].disabled = True
        elif user is not None:
            self.fields['group'].queryset = user.profile.moderated_groups().order_by('name')
            if initial_group is not None:
                self.initial.setdefault('group', initial_group.pk)
        if self.instance and self.instance.pk and self.instance.start_at:
            self.initial['start_at'] = self.instance.start_at.strftime('%Y-%m-%dT%H:%M')
        # Modo inicial: si el evento ya tiene ruta asociada, arrancar en "existente".
        if not self.is_bound:
            self.initial.setdefault(
                'route_mode',
                'existing' if getattr(self.instance, 'associated_route_id', None) else 'none',
            )
        # La clase de estilo `input` aplica a los campos de texto/select; los radios
        # y el input de archivo se estilizan aparte en la plantilla/CSS.
        for name, field in self.fields.items():
            if name in ('route_mode', 'gpx_file'):
                continue
            css = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (css + ' input').strip()

    def clean(self):
        cleaned = super().clean()
        mode = cleaned.get('route_mode') or 'none'
        if mode == 'new':
            gpx = cleaned.get('gpx_file')
            if not gpx:
                self.add_error('gpx_file', 'Selecciona un archivo GPX para crear la ruta nueva.')
            else:
                try:
                    validate_gpx_upload(gpx)
                except forms.ValidationError as exc:
                    self.add_error('gpx_file', exc)
            # Al subir un GPX nuevo se ignora cualquier ruta existente seleccionada.
            cleaned['associated_route'] = None
        elif mode == 'none':
            cleaned['associated_route'] = None
            cleaned['gpx_file'] = None
        else:  # 'existing'
            cleaned['gpx_file'] = None
        return cleaned

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if not image:
            return image

        header = image.read(MAGIC_BYTES_LENGTH)
        image.seek(0)
        kind = filetype.guess(header)
        if kind is None:
            raise forms.ValidationError(
                'No se pudo determinar el tipo del archivo. Comprueba que la imagen no esté corrupta.'
            )
        if kind.mime not in ALLOWED_IMAGE_TYPES:
            raise forms.ValidationError(
                f'Formato de imagen no válido ({kind.mime}). Usa JPG, PNG, WebP o GIF.'
            )
        return image
