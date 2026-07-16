from django.db.models import Sum, Count
from django.utils import timezone
from django.views.generic import TemplateView

from apps.accounts.mixins import ApprovedUserMixin
from apps.events.models import Event, EventRSVP
from apps.media_gallery.models import MediaItem
from apps.blog.models import Post
from apps.members.services import members_visible_to
from apps.routes.models import Route


class DashboardView(ApprovedUserMixin, TemplateView):
    template_name = 'dashboard/home.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        now = timezone.now()
        user = self.request.user

        # Vista COMBINADA: contenido de TODAS las grupetas del usuario a la
        # vez (a diferencia de eventos/chat/miembros/blog/galería, que se
        # navegan por una "grupeta activa"). Ver GroupScopedQuerySet.for_user().
        upcoming = Event.objects.for_user(user).filter(
            start_at__gte=now, state__in=Event.DEFAULT_LIST_STATES
        ).select_related('created_by', 'associated_route', 'group').order_by('start_at')

        next_event = upcoming.first()
        ctx['next_event'] = next_event
        # Solo los primeros asistentes confirmados (para los avatares), sin cargar todos los RSVP.
        ctx['next_event_attendees'] = (
            list(
                next_event.rsvps.filter(response=EventRSVP.Response.SI)
                .select_related('member')
                .order_by('created_at')[:5]
            )
            if next_event else []
        )
        ctx['upcoming_events'] = upcoming[1:4]
        ctx['recent_media'] = MediaItem.objects.for_user(user).filter(
            media_type='image'
        ).select_related('uploaded_by', 'group').order_by('-created_at')[:8]
        ctx['recent_posts'] = Post.objects.for_user(user).select_related(
            'author', 'group'
        ).order_by('-created_at')[:4]
        ctx['top_members'] = members_visible_to(user).select_related('user').order_by('-total_km')[:3]

        agg = Route.objects.for_user(user).aggregate(
            total_km=Sum('distance_km'),
            total_elevation=Sum('elevation_gain_m'),
            total_routes=Count('pk'),
        )
        ctx['club_stats'] = {
            'km': int(agg['total_km'] or 0),
            'elevation': int(agg['total_elevation'] or 0),
            'routes': agg['total_routes'],
            'members': members_visible_to(user).count(),
        }

        ctx['display_name'] = user.first_name or user.username or 'ciclista'
        return ctx
