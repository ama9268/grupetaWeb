from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import ListView, DetailView, CreateView
from django.urls import reverse_lazy

from apps.accounts.mixins import ApprovedUserMixin
from .models import Route
from .forms import RouteForm
from .services import create_route_from_gpx


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
        route, parsed = create_route_from_gpx(
            author=self.request.user,
            gpx_file=form.cleaned_data['gpx_file'],
            title=form.cleaned_data['title'],
            description=form.cleaned_data.get('description', ''),
        )
        if not parsed:
            messages.warning(self.request, 'No se pudieron extraer las estadísticas del GPX.')
        messages.success(self.request, f'Ruta "{route.title}" publicada correctamente.')
        return redirect(self.success_url)
