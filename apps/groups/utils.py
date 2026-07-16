from django.utils.text import slugify


def get_available_groups(profile):
    """Grupetas navegables por el usuario: todas las activas si es Admin
    global, o solo aquellas donde tiene una Membership aprobada."""
    from .models import Group
    qs = Group.objects.active() if profile.is_admin else profile.approved_groups()
    return qs.order_by('name')


def resolve_active_group(request, profile, available_groups=None):
    """Grupeta activa para páginas de contenido acotado (Eventos, Chat,
    Miembros, Blog, Galería). Se guarda en sesión y se revalida en cada
    request contra `available_groups` (si deja de ser válida, cae al valor
    por defecto: la grupeta de la membresía aprobada más antigua)."""
    from .models import Membership

    if available_groups is None:
        available_groups = get_available_groups(profile)

    slug = request.session.get('active_group_slug')
    if slug:
        group = available_groups.filter(slug=slug).first()
        if group is not None:
            return group

    membership = (
        Membership.objects.filter(user=profile.user, status=Membership.Status.APPROVED)
        .order_by('created_at')
        .select_related('group')
        .first()
    )
    if membership is not None and available_groups.filter(pk=membership.group_id).exists():
        return membership.group
    return available_groups.first()


def unique_group_slug(name):
    from .models import Group
    base = slugify(name)[:130] or 'grupeta'
    slug = base
    i = 2
    while Group.objects.filter(slug=slug).exists():
        slug = f'{base}-{i}'
        i += 1
    return slug
