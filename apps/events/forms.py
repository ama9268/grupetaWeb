import filetype
from django import forms
from django.utils import timezone as dj_timezone

from apps.media_gallery.cloudinary_utils import ALLOWED_IMAGE_TYPES
from apps.routes.services import validate_gpx_upload
from .models import Event

MAGIC_BYTES_LENGTH = 261  # filetype solo necesita los primeros ~261 bytes


def _state_transition_choices(current_state):
    """Estados a los que se puede pasar editando el formulario, desde `current_state`.

    Solo hacia delante, nunca hacia atrás (no existe "des-realizar" ni "desarchivar" —
    ver `Event.mark_realizado`/`archive`, que son irreversibles a propósito). Se
    recalculan en el servidor a partir del estado real en BD, no del que mande el
    cliente, así que un intento de retroceder (POST con un estado no permitido desde
    el actual) lo rechaza el propio `ChoiceField` como opción inválida.
    """
    labels = dict(Event.State.choices)
    if current_state == Event.State.PENDIENTE:
        allowed = [Event.State.PENDIENTE, Event.State.REALIZADO, Event.State.ARCHIVADO]
    elif current_state == Event.State.REALIZADO:
        allowed = [Event.State.REALIZADO, Event.State.ARCHIVADO]
    else:
        allowed = [Event.State.ARCHIVADO]
    return [(value, labels[value]) for value in allowed]


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
        # "Ruta especial" se crea y gestiona exclusivamente desde Salidas (ver SalidaForm),
        # que además ofrece el agente de recomendación de ruta con sus propios campos.
        if 'event_type' in self.fields:
            self.fields['event_type'].choices = [
                (value, label) for value, label in Event.EventType.choices
                if value != Event.EventType.RUTA_ESPECIAL
            ]

        route_group = None
        if self.instance and self.instance.pk:
            # La grupeta de un evento ya creado no se cambia (chat/álbum/RSVP
            # ya están ligados a ella): se muestra de solo lectura.
            self.fields['group'].disabled = True
            route_group = self.instance.group_id
        elif user is not None:
            self.fields['group'].queryset = user.profile.moderated_groups().order_by('name')
            if initial_group is not None:
                self.initial.setdefault('group', initial_group.pk)
                route_group = initial_group.pk
        # El desplegable de "ruta existente" solo debe mostrar rutas de la grupeta del
        # evento, nunca las de otra grupeta (Route ya lleva FK a group).
        from apps.routes.models import Route
        self.fields['associated_route'].queryset = (
            Route.objects.filter(group=route_group) if route_group else Route.objects.none()
        )
        if self.instance and self.instance.pk and self.instance.start_at:
            # start_at llega de la BD en UTC (aware); localtime() lo pasa a hora de
            # TIME_ZONE antes de formatear el valor inicial del <input type="datetime-
            # local">. Un .strftime() directo mostraría la hora UTC cruda (p.ej. una
            # Salida creada a las 08:00 locales reaparecería como 06:00 en verano).
            self.initial['start_at'] = dj_timezone.localtime(self.instance.start_at).strftime('%Y-%m-%dT%H:%M')
        # Cambiar el estado desde el propio formulario de edición (además de los
        # botones dedicados de la ficha) — solo al editar (no tiene sentido al crear,
        # siempre nace "pendiente") y solo Admin/Moderador de esa grupeta llegan aquí
        # (GroupModeratorRequiredMixin ya protege toda la vista de edición). NO es un
        # campo del ModelForm (fuera de Meta.fields): así el guardado normal nunca
        # toca `state` directamente, y es la vista la que decide si hay que enrutar el
        # cambio a través de `mark_realizado()`/`archive()` para no perderse sus
        # efectos colaterales (álbum, archivado del chat) — ver EventUpdateView.
        if self.instance and self.instance.pk:
            self.fields['state'] = forms.ChoiceField(
                choices=_state_transition_choices(self.instance.state),
                initial=self.instance.state,
                label='Estado',
                required=False,  # ausente/vacío = sin cambio de estado (ver EventUpdateView.form_valid)
            )
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


class SalidaForm(EventForm):
    """Formulario de "Salidas" (Event con event_type=RUTA_ESPECIAL fijo, no elegible aquí —
    lo fija la vista antes de guardar, ver apps/events/views.py). Añade los campos propios
    del agente de recomendación de ruta y una 4ª opción de `route_mode` que lo activa.
    """
    ROUTE_MODE_CHOICES = EventForm.ROUTE_MODE_CHOICES + (
        ('recommend', 'Recomendar ruta (viento)'),
    )
    route_mode = forms.ChoiceField(
        choices=ROUTE_MODE_CHOICES, required=False,
        widget=forms.RadioSelect, initial='none', label='Ruta',
    )

    class Meta(EventForm.Meta):
        fields = (
            'group', 'title', 'description', 'start_at', 'location', 'associated_route',
            'pace_level', 'target_distance_km', 'target_elevation_gain_m',
        )
        widgets = EventForm.Meta.widgets
        labels = {
            **EventForm.Meta.labels,
            'location': 'Punto de encuentro',
            'pace_level': 'Nivel / ritmo',
            'target_distance_km': 'Distancia objetivo (km)',
            'target_elevation_gain_m': 'Desnivel objetivo (m)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pace_level'].required = True
        self.fields['target_distance_km'].required = False
        self.fields['target_elevation_gain_m'].required = False
        # Radios del panel "Recomendar ruta" (ver partials/route_recommendation_results.html):
        # campo APARTE de `associated_route` — si compartieran `name`, el <select> oculto
        # del panel "existente" y estos radios postearían ambos bajo la misma clave y
        # ganaría el último en orden del DOM, algo frágil y confuso. Mismo queryset
        # acotado por grupeta que `associated_route` (ver EventForm.__init__).
        self.fields['recommended_route'] = forms.ModelChoiceField(
            queryset=self.fields['associated_route'].queryset, required=False,
        )
        self.fields['recommended_route'].widget.attrs['class'] = 'input'

    def clean(self):
        cleaned = super().clean()
        if (cleaned.get('route_mode') or 'none') == 'recommend':
            cleaned['associated_route'] = cleaned.get('recommended_route')
        return cleaned
