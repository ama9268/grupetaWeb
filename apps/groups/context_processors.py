from .utils import get_available_groups, resolve_active_group


def active_group(request):
    """Expone `nav_active_group`/`nav_available_groups` a TODAS las plantillas,
    para el selector de grupeta activa en la topbar (ver templates/base.html).
    Nombres distintos a los que usa `ActiveGroupMixin` en el contexto de la
    vista, para no chocar con ellos; ambos resuelven al mismo valor dentro de
    la misma request."""
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return {}

    profile = getattr(user, 'profile', None)
    if profile is None or not profile.is_approved:
        return {}

    available_groups = get_available_groups(profile)
    current = resolve_active_group(request, profile, available_groups)
    # Materializado a lista: este valor se expone a TODAS las plantillas
    # (incluidos templates internos como los mensajes de allauth), y una
    # QuerySet sin evaluar puede acabar disparando una consulta a BD fuera
    # del ciclo de vida normal de la request (p.ej. en el post-procesado
    # asíncrono de django-debug-toolbar bajo ASGI/Channels).
    return {'nav_active_group': current, 'nav_available_groups': list(available_groups)}
