from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView

from apps.accounts.mixins import ApprovedUserMixin
from .forms import GroupCreateForm
from .models import Group, Membership
from .utils import get_available_groups, unique_group_slug


def _safe_redirect_target(request, candidate):
    if candidate and url_has_allowed_host_and_scheme(
        candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
    ):
        return candidate
    return None


@login_required
@require_POST
def set_active_group(request):
    """Cambia la grupeta activa (sesión) para las páginas de contenido acotado
    (Eventos, Chat, Miembros, Blog, Galería). No afecta al Dashboard."""
    profile = request.user.profile
    group = get_object_or_404(get_available_groups(profile), slug=request.POST.get('slug', ''))
    request.session['active_group_slug'] = group.slug

    next_url = (
        _safe_redirect_target(request, request.POST.get('next'))
        or _safe_redirect_target(request, request.META.get('HTTP_REFERER'))
        or reverse('dashboard:home')
    )

    if request.headers.get('HX-Request'):
        response = HttpResponse(status=204)
        response['HX-Redirect'] = next_url
        return response
    return redirect(next_url)


class GroupListView(ApprovedUserMixin, ListView):
    """Directorio de grupetas activas: para descubrir y solicitar unirse a más."""
    model = Group
    template_name = 'groups/group_list.html'

    def get_queryset(self):
        return Group.objects.active().order_by('name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        memberships = {
            m.group_id: m for m in Membership.objects.filter(user=self.request.user)
        }
        ctx['groups'] = [
            {'group': group, 'membership': memberships.get(group.pk)}
            for group in ctx['object_list']
        ]
        return ctx


class GroupCreateView(ApprovedUserMixin, CreateView):
    """Autoservicio: cualquier miembro aprobado (en al menos una grupeta) puede
    crear una grupeta nueva y se convierte automáticamente en su moderador."""
    model = Group
    form_class = GroupCreateForm
    template_name = 'groups/group_create.html'

    def form_valid(self, form):
        group = form.save(commit=False)
        group.slug = unique_group_slug(group.name)
        group.created_by = self.request.user
        group.save()

        Membership.objects.create(
            user=self.request.user,
            group=group,
            role=Membership.Role.MODERATOR,
            status=Membership.Status.APPROVED,
            decided_at=timezone.now(),
            decided_by=self.request.user,
        )
        messages.success(self.request, f'Grupeta «{group.name}» creada. Ya eres su moderador.')
        return redirect('groups:detail', slug=group.slug)


class GroupDetailView(ApprovedUserMixin, DetailView):
    model = Group
    template_name = 'groups/group_detail.html'
    context_object_name = 'group'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return Group.objects.active()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['membership'] = Membership.objects.filter(
            user=self.request.user, group=self.object,
        ).first()
        ctx['moderators'] = Membership.objects.filter(
            group=self.object, role=Membership.Role.MODERATOR, status=Membership.Status.APPROVED,
        ).select_related('user')
        ctx['members_count'] = Membership.objects.filter(
            group=self.object, status=Membership.Status.APPROVED,
        ).count()
        return ctx


@login_required
@require_POST
def request_join_group(request, slug):
    """Solicita unirse a una grupeta ADICIONAL (además de la elegida en el
    registro). Queda pendiente hasta que un moderador de esa grupeta la
    apruebe."""
    if not request.user.profile.is_approved:
        raise PermissionDenied

    group = get_object_or_404(Group.objects.active(), slug=slug)
    membership, created = Membership.objects.get_or_create(
        user=request.user, group=group,
        defaults={'role': Membership.Role.MEMBER, 'status': Membership.Status.PENDING},
    )

    if created:
        messages.success(request, f'Solicitud enviada a {group.name}.')
    elif membership.status == Membership.Status.REJECTED:
        membership.status = Membership.Status.PENDING
        membership.decided_at = None
        membership.decided_by = None
        membership.save(update_fields=['status', 'decided_at', 'decided_by'])
        from apps.accounts.emails import send_approval_request_email
        send_approval_request_email(membership)
        messages.success(request, f'Solicitud reenviada a {group.name}.')
    else:
        messages.info(request, f'Ya tienes una relación con {group.name}.')

    return redirect('groups:detail', slug=group.slug)
