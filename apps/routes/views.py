from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import ListView, DetailView, CreateView
from django.urls import reverse_lazy

from apps.accounts.mixins import ApprovedUserMixin
from .models import Route
from .forms import RouteForm
from .gpx_utils import parse_gpx


class RouteListView(ApprovedUserMixin, ListView):
    model = Route
    template_name = 'routes/route_list.html'
    context_object_name = 'routes'
    paginate_by = 20

    def get_queryset(self):
        return Route.objects.select_related('author').all()


class RouteDetailView(ApprovedUserMixin, DetailView):
    model = Route
    template_name = 'routes/route_detail.html'
    context_object_name = 'route'


class RouteCreateView(ApprovedUserMixin, CreateView):
    model = Route
    form_class = RouteForm
    template_name = 'routes/route_create.html'
    success_url = reverse_lazy('routes:list')

    def form_valid(self, form):
        route = form.save(commit=False)
        route.author = self.request.user

        try:
            gpx_data = parse_gpx(form.cleaned_data['gpx_file'])
            route.distance_km = gpx_data['distance_km']
            route.elevation_gain_m = gpx_data['elevation_gain_m']
            route.elevation_loss_m = gpx_data['elevation_loss_m']
            route.max_elevation_m = gpx_data['max_elevation_m']
            route.min_elevation_m = gpx_data['min_elevation_m']
            route.track_geojson = gpx_data['track_points']
            route.elevation_profile = gpx_data['elevation_profile']
        except Exception:
            messages.warning(self.request, 'No se pudieron extraer las estadísticas del GPX.')

        route.save()

        messages.success(self.request, f'Ruta "{route.title}" publicada correctamente.')
        return redirect(self.success_url)
