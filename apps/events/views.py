from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.generic import ListView, DetailView, CreateView, UpdateView

from apps.accounts.mixins import ApprovedUserMixin, ModeratorRequiredMixin
from apps.accounts.decorators import approved_required
from apps.groups.mixins import ActiveGroupMixin, GroupModeratorRequiredMixin
from apps.groups.models import Group
from apps.groups.permissions import require_group_member, require_group_moderator
from apps.media_gallery.cloudinary_utils import upload_image, delete_asset
from apps.media_gallery.forms import MediaUploadForm
from apps.media_gallery.services import upload_media_item
from apps.routes.services import create_route_from_gpx, duplicate_warning_message

from .models import Event, EventRSVP
from .forms import EventForm, SalidaForm
from .recommender.exceptions import LLMUnavailable
from .recommender.llm.factory import get_llm_client
from .recommender.service import recommend_routes

# (valor, etiqueta, icono) para el widget RSVP.
RSVP_OPTIONS = [
    (EventRSVP.Response.SI, 'Voy', '✓'),
    (EventRSVP.Response.QUIZAS, 'Quizás', '?'),
    (EventRSVP.Response.NO, 'No voy', '✕'),
]


def _apply_route_selection(event, form, request):
    """Fija event.associated_route según el modo elegido en el formulario.

    En modo 'new' crea una Route a partir del GPX (título/descr. del evento) y la
    asocia. El resto de modos ('none'/'existing'/'recommend') ya vienen normalizados
    desde EventForm.clean() — 'recommend' solo aporta las candidatas en el propio
    <select>/radios de associated_route, no cambia esta función.
    """
    mode = form.cleaned_data.get('route_mode') or 'none'
    if mode == 'new' and form.cleaned_data.get('gpx_file'):
        route, parsed, duplicate = create_route_from_gpx(
            group=event.group,
            author=request.user,
            gpx_file=form.cleaned_data['gpx_file'],
            title=event.title,
            description=event.description,
        )
        event.associated_route = route
        if not parsed:
            messages.warning(request, 'La ruta se creó, pero no se pudieron extraer sus estadísticas del GPX.')
        if duplicate:
            messages.warning(request, duplicate_warning_message(duplicate))


# --- Eventos / Salidas: misma tabla (Event), dos secciones de navegación. Las vistas de
# Salidas heredan de las de Eventos y solo fijan `fixed_event_type`/`url_namespace` (y, en
# creación/edición, `form_class`) — ver apps/events/CLAUDE.md, sección "Salidas". ---

class EventListView(ApprovedUserMixin, ActiveGroupMixin, ListView):
    model = Event
    context_object_name = 'events'
    fixed_event_type = None
    url_namespace = 'events'
    heading = 'Eventos'
    heading_description = 'Rutas especiales, viajes y carreras de la grupeta'
    create_label = '+ Crear evento'

    def get_queryset(self):
        estado = self.request.GET.get('estado', 'activos')
        qs = Event.objects.filter(group=self.active_group).select_related('created_by', 'associated_route')
        if self.fixed_event_type:
            qs = qs.filter(event_type=self.fixed_event_type)
        else:
            qs = qs.exclude(event_type=Event.EventType.RUTA_ESPECIAL)
        if estado == 'todos':
            pass
        elif estado in Event.State.values:
            qs = qs.filter(state=estado)
        else:  # 'activos' → filtro por defecto: pendientes + aceptados
            qs = qs.filter(state__in=Event.DEFAULT_LIST_STATES)
        return qs.order_by('start_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['estado'] = self.request.GET.get('estado', 'activos')
        ctx['state_choices'] = Event.State.choices
        ctx['heading'] = self.heading
        ctx['heading_description'] = self.heading_description
        ctx['create_label'] = self.create_label
        ctx['list_url_name'] = f'{self.url_namespace}:list'
        ctx['create_url_name'] = f'{self.url_namespace}:create'
        return ctx

    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            return ['events/partials/event_list_items.html']
        return ['events/event_list.html']


class SalidaListView(EventListView):
    fixed_event_type = Event.EventType.RUTA_ESPECIAL
    url_namespace = 'salidas'
    heading = 'Salidas'
    heading_description = 'Quedadas de la grupeta para salir en bici'
    create_label = '+ Crear salida'


class EventDetailView(ApprovedUserMixin, DetailView):
    model = Event
    template_name = 'events/event_detail.html'
    context_object_name = 'event'
    fixed_event_type = None
    url_namespace = 'events'
    back_label = '← Eventos'

    def get_queryset(self):
        # Acceso por enlace directo: cualquier grupeta a la que pertenezca el
        # usuario (no solo la "activa"), a diferencia del listado.
        qs = Event.objects.filter(
            group__in=self.request.user.profile.approved_groups()
        ).select_related('created_by', 'associated_route', 'group')
        if self.fixed_event_type:
            qs = qs.filter(event_type=self.fixed_event_type)
        else:
            qs = qs.exclude(event_type=Event.EventType.RUTA_ESPECIAL)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        event = self.object
        ctx['user_rsvp'] = EventRSVP.objects.filter(
            event=event, member=self.request.user
        ).first()
        ctx['attendees'] = event.rsvps.filter(
            response=EventRSVP.Response.SI
        ).select_related('member').order_by('created_at')
        ctx['maybe_count'] = event.rsvps.filter(response=EventRSVP.Response.QUIZAS).count()
        ctx['no_count'] = event.rsvps.filter(response=EventRSVP.Response.NO).count()

        album = event.album
        ctx['album'] = album
        ctx['media_items'] = album.items.select_related('uploaded_by') if album else []
        ctx['media_form'] = MediaUploadForm()
        ctx['can_moderate'] = self.request.user.profile.is_group_moderator(event.group)
        ctx['can_upload'] = album is not None and not event.is_archived
        ctx['rsvp_options'] = RSVP_OPTIONS
        ctx['back_label'] = self.back_label
        ctx['list_url_name'] = f'{self.url_namespace}:list'
        ctx['edit_url_name'] = f'{self.url_namespace}:edit'
        return ctx


class SalidaDetailView(EventDetailView):
    fixed_event_type = Event.EventType.RUTA_ESPECIAL
    url_namespace = 'salidas'
    back_label = '← Salidas'


class EventCreateView(ModeratorRequiredMixin, ActiveGroupMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = 'events/event_create.html'
    fixed_event_type = None
    entity_label = 'Evento'
    entity_created_label = 'creado'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['initial_group'] = self.active_group
        return kwargs

    def form_valid(self, form):
        event = form.save(commit=False)
        if self.fixed_event_type:
            event.event_type = self.fixed_event_type
        event.created_by = self.request.user
        image = form.cleaned_data.get('image')
        if image:
            event.image_public_id, event.image_url = upload_image(image)
        _apply_route_selection(event, form, self.request)
        event.save()
        messages.success(
            self.request, f'{self.entity_label} "{event.title}" {self.entity_created_label} correctamente.'
        )
        return redirect(event.get_absolute_url())


class SalidaCreateView(EventCreateView):
    form_class = SalidaForm
    template_name = 'salidas/salida_create.html'
    fixed_event_type = Event.EventType.RUTA_ESPECIAL
    entity_label = 'Salida'
    entity_created_label = 'creada'


class EventUpdateView(ApprovedUserMixin, GroupModeratorRequiredMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name = 'events/event_edit.html'
    fixed_event_type = None
    entity_label = 'Evento'
    entity_updated_label = 'actualizado'

    def get_queryset(self):
        # Acceso restringido al mismo subconjunto de tipos que su sección (evita que,
        # p.ej., una "carrera" se edite desde /salidas/<pk>/editar/ y SalidaForm le
        # reasigne el tipo a ruta_especial sin querer).
        qs = Event.objects.all()
        if self.fixed_event_type:
            return qs.filter(event_type=self.fixed_event_type)
        return qs.exclude(event_type=Event.EventType.RUTA_ESPECIAL)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        event = form.save(commit=False)
        if self.fixed_event_type:
            event.event_type = self.fixed_event_type
        image = form.cleaned_data.get('image')
        if image:
            old_public_id = event.image_public_id
            event.image_public_id, event.image_url = upload_image(image)
            # Limpiar la imagen anterior en Cloudinary para no dejarla huérfana.
            if old_public_id and old_public_id != event.image_public_id:
                delete_asset(old_public_id)
        _apply_route_selection(event, form, self.request)
        event.save()
        messages.success(self.request, f'{self.entity_label} {self.entity_updated_label} correctamente.')
        return redirect(event.get_absolute_url())


class SalidaUpdateView(EventUpdateView):
    form_class = SalidaForm
    template_name = 'salidas/salida_edit.html'
    fixed_event_type = Event.EventType.RUTA_ESPECIAL
    entity_label = 'Salida'
    entity_updated_label = 'actualizada'


# --- Acciones compartidas: operan por pk sin importar el tipo de evento, así que se
# registran una única vez (namespace `events`) y sirven igual a Eventos que a Salidas.
# Los redirects usan Event.get_absolute_url() para volver siempre a la sección correcta. ---

@approved_required
def event_accept(request, pk):
    event = get_object_or_404(Event, pk=pk)
    require_group_moderator(request.user, event.group)
    if request.method == 'POST':
        event.accept(by_user=request.user)
        messages.success(request, f'"{event.title}" aceptado. Se ha creado su álbum.')
    return redirect(event.get_absolute_url())


@approved_required
def event_cancel(request, pk):
    event = get_object_or_404(Event, pk=pk)
    require_group_moderator(request.user, event.group)
    if request.method == 'POST':
        event.cancel()
        messages.success(request, f'"{event.title}" cancelado.')
    return redirect(event.get_absolute_url())


@approved_required
def event_media_upload(request, pk):
    event = get_object_or_404(Event, pk=pk)
    require_group_member(request.user, event.group)
    if request.method != 'POST':
        return redirect(event.get_absolute_url())

    if event.album is None or event.is_archived:
        messages.error(request, 'Esto no admite subida de fotos o vídeos.')
        return redirect(event.get_absolute_url())

    form = MediaUploadForm(request.POST, request.FILES)
    if form.is_valid():
        upload_media_item(
            user=request.user,
            media_type=form.cleaned_data['media_type'],
            file=form.cleaned_data['file'],
            title=form.cleaned_data.get('title', ''),
            group=event.group,
            album=event.album,
        )
        messages.success(request, 'Archivo subido correctamente.')
    else:
        messages.error(request, form.errors.get('__all__', ['No se pudo subir el archivo.'])[0])
    return redirect(event.get_absolute_url())


@approved_required
def rsvp_view(request, event_id, response):
    event = get_object_or_404(Event, pk=event_id)
    if request.method != 'POST':
        return redirect(event.get_absolute_url())

    require_group_member(request.user, event.group)
    if response not in EventRSVP.Response.values:
        return redirect(event.get_absolute_url())

    rsvp, created = EventRSVP.objects.get_or_create(
        event=event, member=request.user, defaults={'response': response}
    )
    if not created and rsvp.response != response:
        rsvp.response = response
        rsvp.save()

    attendees = event.rsvps.filter(
        response=EventRSVP.Response.SI
    ).select_related('member').order_by('created_at')
    return render(request, 'events/partials/rsvp_widget.html', {
        'event': event,
        'user_rsvp': rsvp,
        'attendees': attendees,
        'rsvp_options': RSVP_OPTIONS,
    })


# --- Agente de recomendación de ruta (solo Salidas). Endpoints "sueltos": la Salida puede
# no existir todavía en BD mientras se rellena el formulario, así que reciben grupeta/fecha/
# objetivos como POST normales (ver templates/salidas/*, hx-include="closest form") y
# revalidan permisos en servidor — no hay Event ni GroupModeratorRequiredMixin de por medio. ---

def _parse_start_at(raw):
    if not raw:
        return None
    dt = parse_datetime(raw)
    if dt is None:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    return dt


def _decimal_or_none(raw):
    try:
        return Decimal(raw) if raw else None
    except (InvalidOperation, TypeError):
        return None


def _int_or_none(raw):
    try:
        return int(raw) if raw else None
    except (TypeError, ValueError):
        return None


def _recommend_from_request(request):
    group = get_object_or_404(Group, pk=request.POST.get('group'))
    require_group_moderator(request.user, group)
    start_at = _parse_start_at(request.POST.get('start_at'))
    if start_at is None:
        return None, None
    result = recommend_routes(
        group=group,
        start_at=start_at,
        target_distance_km=_decimal_or_none(request.POST.get('target_distance_km')),
        target_elevation_gain_m=_int_or_none(request.POST.get('target_elevation_gain_m')),
    )
    return group, result


@approved_required
def route_recommend(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    group, result = _recommend_from_request(request)
    return render(request, 'events/partials/route_recommendation_results.html', {
        'result': result,
        'llm_enabled': settings.ROUTE_RECOMMENDER_LLM_PROVIDER != 'none',
        'missing_start_at': result is None,
    })


@approved_required
def route_recommend_explain(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    group, result = _recommend_from_request(request)
    text = None
    if result is not None:
        try:
            text = get_llm_client().explain(result=result)
        except LLMUnavailable:
            text = None
    return render(request, 'events/partials/route_recommendation_explanation.html', {'text': text})
