from django.utils import timezone
from django.views.generic import TemplateView

from apps.accounts.mixins import ApprovedUserMixin
from apps.accounts.models import UserProfile
from apps.events.models import Event
from apps.media_gallery.models import MediaItem
from apps.blog.models import Post


class DashboardView(ApprovedUserMixin, TemplateView):
    template_name = 'dashboard/home.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        now = timezone.now()
        ctx['upcoming_events'] = Event.objects.filter(
            date__gte=now
        ).select_related('created_by').order_by('date')[:5]
        ctx['recent_media'] = MediaItem.objects.order_by('-created_at')[:8]
        ctx['recent_posts'] = Post.objects.select_related('author').order_by('-created_at')[:5]
        ctx['top_members'] = UserProfile.objects.filter(
            status='approved'
        ).select_related('user').order_by('-total_km')[:10]
        return ctx
