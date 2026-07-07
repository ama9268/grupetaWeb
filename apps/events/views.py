from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView

from apps.accounts.mixins import ApprovedUserMixin, ModeratorRequiredMixin
from apps.accounts.decorators import approved_required, moderator_required
from apps.media_gallery.cloudinary_utils import upload_image, delete_asset
from apps.media_gallery.forms import MediaUploadForm
from apps.media_gallery.services import upload_media_item
from apps.routes.services import create_route_from_gpx

from .models import Event, EventRSVP
from .forms import EventForm

# (valor, etiqueta, icono) para el widget RSVP.
RSVP_OPTIONS = [
    (EventRSVP.Response.SI, 'Voy', '✓'),
    (EventRSVP.Response.QUIZAS, 'Quizás', '?'),
    (EventRSVP.Response.NO, 'No voy', '✕'),
]


def _apply_route_selection(event, form, request):
    """Fija event.associated_route según el modo elegido en el formulario.

    En modo 'new' crea una Route a partir del GPX (título/descr. del evento) y la
    asocia. El resto de modos ya vienen normalizados desde EventForm.clean().
    """
    mode = form.cleaned_data.get('route_mode') or 'none'
    if mode == 'new' and form.cleaned_data.get('gpx_file'):
        route, parsed = create_route_from_gpx(
            author=request.user,
            gpx_file=form.cleaned_data['gpx_file'],
            title=event.title,
            description=event.description,
        )
        event.associated_route = route
        if not parsed:
            messages.warning(request, 'La ruta se creó, pero no se pudieron extraer sus estadísticas del GPX.')


class EventListView(ApprovedUserMixin, ListView):
    model = Event
    context_object_name = 'events'

    def get_queryset(self):
        estado = self.request.GET.get('estado', 'activos')
        qs = Event.objects.select_related('created_by', 'associated_route')
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
        return ctx

    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            return ['events/partials/event_list_items.html']
        return ['events/event_list.html']


class EventDetailView(ApprovedUserMixin, DetailView):
    model = Event
    template_name = 'events/event_detail.html'
    context_object_name = 'event'

    def get_queryset(self):
        return Event.objects.select_related('created_by', 'associated_route')

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
        ctx['can_moderate'] = getattr(self.request.user.profile, 'is_moderator', False)
        ctx['can_upload'] = album is not None and not event.is_archived
        ctx['rsvp_options'] = RSVP_OPTIONS
        return ctx


class EventCreateView(ModeratorRequiredMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = 'events/event_create.html'

    def form_valid(self, form):
        event = form.save(commit=False)
        event.created_by = self.request.user
        image = form.cleaned_data.get('image')
        if image:
            event.image_public_id, event.image_url = upload_image(image)
        _apply_route_selection(event, form, self.request)
        event.save()
        messages.success(self.request, f'Evento "{event.title}" creado correctamente.')
        return redirect('events:detail', pk=event.pk)


class EventUpdateView(ModeratorRequiredMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name = 'events/event_edit.html'

    def form_valid(self, form):
        event = form.save(commit=False)
        image = form.cleaned_data.get('image')
        if image:
            old_public_id = event.image_public_id
            event.image_public_id, event.image_url = upload_image(image)
            # Limpiar la imagen anterior en Cloudinary para no dejarla huérfana.
            if old_public_id and old_public_id != event.image_public_id:
                delete_asset(old_public_id)
        _apply_route_selection(event, form, self.request)
        event.save()
        messages.success(self.request, 'Evento actualizado correctamente.')
        return redirect('events:detail', pk=event.pk)


@moderator_required
def event_accept(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method == 'POST':
        event.accept(by_user=request.user)
        messages.success(request, f'Evento "{event.title}" aceptado. Se ha creado su álbum.')
    return redirect('events:detail', pk=pk)


@moderator_required
def event_cancel(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method == 'POST':
        event.cancel()
        messages.success(request, f'Evento "{event.title}" cancelado.')
    return redirect('events:detail', pk=pk)


@approved_required
def event_media_upload(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method != 'POST':
        return redirect('events:detail', pk=pk)

    if event.album is None or event.is_archived:
        messages.error(request, 'Este evento no admite subida de fotos o vídeos.')
        return redirect('events:detail', pk=pk)

    form = MediaUploadForm(request.POST, request.FILES)
    if form.is_valid():
        upload_media_item(
            user=request.user,
            media_type=form.cleaned_data['media_type'],
            file=form.cleaned_data['file'],
            title=form.cleaned_data.get('title', ''),
            album=event.album,
        )
        messages.success(request, 'Archivo subido correctamente.')
    else:
        messages.error(request, form.errors.get('__all__', ['No se pudo subir el archivo.'])[0])
    return redirect('events:detail', pk=pk)


@approved_required
def rsvp_view(request, event_id, response):
    if request.method != 'POST':
        return redirect('events:detail', pk=event_id)

    event = get_object_or_404(Event, pk=event_id)
    if response not in EventRSVP.Response.values:
        return redirect('events:detail', pk=event_id)

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
