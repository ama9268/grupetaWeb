import secrets

from django.contrib import messages
from django.contrib.gis.geos import Point
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView, CreateView

from apps.accounts.mixins import ApprovedUserMixin, ModeratorRequiredMixin
from apps.groups.mixins import ActiveGroupMixin

from .models import Route, StravaImportCandidate
from .forms import RouteForm
from .services import create_route_from_gpx, create_route_from_strava_gpx, duplicate_warning_message
from .strava import StravaService, build_gpx_from_streams


class RouteListView(ApprovedUserMixin, ActiveGroupMixin, ListView):
    model = Route
    template_name = 'routes/route_list.html'
    context_object_name = 'routes'
    paginate_by = 20

    def get_queryset(self):
        return Route.objects.select_related('author').filter(group=self.active_group)


class RouteDetailView(ApprovedUserMixin, DetailView):
    model = Route
    template_name = 'routes/route_detail.html'
    context_object_name = 'route'

    def get_queryset(self):
        return Route.objects.for_user(self.request.user).select_related('author', 'group')


class RouteCreateView(ModeratorRequiredMixin, ActiveGroupMixin, CreateView):
    model = Route
    form_class = RouteForm
    template_name = 'routes/route_create.html'
    success_url = reverse_lazy('routes:list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['initial_group'] = self.active_group
        return kwargs

    def form_valid(self, form):
        route, parsed, duplicate = create_route_from_gpx(
            group=form.cleaned_data['group'],
            author=self.request.user,
            gpx_file=form.cleaned_data['gpx_file'],
            title=form.cleaned_data['title'],
            description=form.cleaned_data.get('description', ''),
        )
        if not parsed:
            messages.warning(self.request, 'No se pudieron extraer las estadísticas del GPX.')
        if duplicate:
            messages.warning(self.request, duplicate_warning_message(duplicate))
        messages.success(self.request, f'Ruta "{route.title}" publicada correctamente.')
        return redirect(self.success_url)


# --- Strava: conectar cuenta, revisar actividades (staging) e importar ---
# Todo el flujo requiere moderar al menos una grupeta (igual que crear rutas):
# conectar Strava no tiene sentido para quien nunca podrá confirmar un import.

class StravaConnectView(ModeratorRequiredMixin, View):
    def get(self, request):
        state = secrets.token_urlsafe(24)
        request.session['strava_oauth_state'] = state
        return redirect(StravaService().authorization_url(state))


class StravaCallbackView(ModeratorRequiredMixin, View):
    def get(self, request):
        if request.GET.get('error'):
            messages.info(request, 'Conexión con Strava cancelada.')
            return redirect('routes:strava_staging')

        expected_state = request.session.pop('strava_oauth_state', None)
        state = request.GET.get('state')
        if not state or not expected_state or state != expected_state:
            messages.error(request, 'No se pudo validar la respuesta de Strava. Inténtalo de nuevo.')
            return redirect('routes:strava_staging')

        code = request.GET.get('code')
        if not code:
            messages.error(request, 'No se recibió código de autorización de Strava.')
            return redirect('routes:strava_staging')

        try:
            StravaService().connect(request.user, code)
        except IntegrityError:
            messages.error(request, 'Esa cuenta de Strava ya está vinculada a otro usuario de la plataforma.')
            return redirect('routes:strava_staging')

        messages.success(request, 'Cuenta de Strava conectada correctamente.')
        return redirect('routes:strava_staging')


class StravaStagingView(ModeratorRequiredMixin, ListView):
    model = StravaImportCandidate
    template_name = 'routes/strava_staging.html'
    context_object_name = 'candidates'

    def get_queryset(self):
        account = getattr(self.request.user, 'strava_account', None)
        if not account:
            return StravaImportCandidate.objects.none()
        return account.candidates.filter(status=StravaImportCandidate.Status.PENDIENTE)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['strava_account'] = getattr(self.request.user, 'strava_account', None)
        ctx['moderated_groups'] = self.request.user.profile.moderated_groups()
        return ctx


class StravaSyncActionView(ModeratorRequiredMixin, View):
    def post(self, request):
        account = getattr(request.user, 'strava_account', None)
        if not account:
            messages.error(request, 'Conecta primero tu cuenta de Strava.')
            return redirect('routes:strava_staging')

        service = StravaService(account)
        existing_ids = set(account.candidates.values_list('strava_activity_id', flat=True))
        created = 0
        for activity in service.list_recent_activities(days=180):
            if activity.id in existing_ids or not activity.start_latlng:
                continue
            try:
                StravaImportCandidate.objects.create(
                    account=account,
                    strava_activity_id=activity.id,
                    name=activity.name,
                    distance_km=round(float(activity.distance) / 1000, 2),
                    elevation_gain_m=(
                        round(float(activity.total_elevation_gain)) if activity.total_elevation_gain else None
                    ),
                    moving_time_s=int(activity.moving_time) if activity.moving_time else None,
                    sport_type=str(activity.sport_type or ''),
                    start_point=Point(activity.start_latlng.lon, activity.start_latlng.lat, srid=4326),
                    started_at=activity.start_date,
                )
                created += 1
            except IntegrityError:
                continue
        messages.success(request, f'{created} actividad(es) nueva(s) sincronizada(s) desde Strava.')
        return redirect('routes:strava_staging')


class StravaImportActionView(ModeratorRequiredMixin, View):
    def post(self, request, pk):
        account = getattr(request.user, 'strava_account', None)
        candidate = get_object_or_404(
            StravaImportCandidate, pk=pk, account=account, status=StravaImportCandidate.Status.PENDIENTE,
        )
        group = get_object_or_404(request.user.profile.moderated_groups(), pk=request.POST.get('group'))

        service = StravaService(account)
        streams = service.get_activity_streams(candidate.strava_activity_id)
        gpx = build_gpx_from_streams(streams, candidate.started_at)

        try:
            route, duplicate = create_route_from_strava_gpx(
                group=group, author=request.user, title=candidate.name, description='',
                gpx=gpx, strava_activity_id=candidate.strava_activity_id,
            )
        except IntegrityError:
            messages.error(request, 'Esta actividad ya se había importado antes.')
            return redirect('routes:strava_staging')

        candidate.status = StravaImportCandidate.Status.IMPORTADO
        candidate.imported_route = route
        candidate.save(update_fields=['status', 'imported_route'])

        if duplicate:
            messages.warning(request, duplicate_warning_message(duplicate))
        messages.success(request, f'Ruta "{route.title}" importada desde Strava.')
        return redirect('routes:strava_staging')


class StravaDiscardActionView(ModeratorRequiredMixin, View):
    def post(self, request, pk):
        account = getattr(request.user, 'strava_account', None)
        candidate = get_object_or_404(
            StravaImportCandidate, pk=pk, account=account, status=StravaImportCandidate.Status.PENDIENTE,
        )
        candidate.status = StravaImportCandidate.Status.DESCARTADO
        candidate.save(update_fields=['status'])
        messages.info(request, f'"{candidate.name}" descartada.')
        return redirect('routes:strava_staging')
