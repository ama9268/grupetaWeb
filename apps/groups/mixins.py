from django.core.exceptions import PermissionDenied

from .utils import get_available_groups, resolve_active_group


class ActiveGroupMixin:
    """Resuelve `self.active_group`/`self.available_groups` para vistas que
    muestran el contenido de UNA sola grupeta a la vez (Eventos, Chat,
    Miembros, Blog, Galería). El Dashboard NO usa este mixin: combina el
    contenido de todas las grupetas del usuario (ver `GroupScopedQuerySet`).

    Debe combinarse con un mixin de autenticación/aprobación (p.ej.
    `ApprovedUserMixin`) más a la izquierda en el MRO.
    """

    def dispatch(self, request, *args, **kwargs):
        profile = request.user.profile
        self.available_groups = get_available_groups(profile)
        self.active_group = resolve_active_group(request, profile, self.available_groups)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_group'] = self.active_group
        # Materializado a lista por la misma razón que en el context
        # processor `active_group` (ver apps/groups/context_processors.py):
        # evita dejar una QuerySet sin evaluar en el contexto de la plantilla.
        ctx['available_groups'] = list(self.available_groups)
        return ctx


class GroupModeratorRequiredMixin:
    """Exige moderar LA grupeta concreta del objeto (edición/aceptación/
    cancelación de un Event, gestión de una ChatRoom, etc.), a diferencia de
    `accounts.mixins.ModeratorRequiredMixin` (modera AL MENOS una grupeta,
    para gating de pantallas de creación).

    Sobrescribir `get_permission_group(obj)` si el grupo no es un FK directo
    `obj.group` (p.ej. `obj.room.group`).
    """

    def get_permission_group(self, obj):
        return obj.group

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not request.user.profile.is_group_moderator(self.get_permission_group(self.object)):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        # Evita un segundo fetch en la vista: dispatch() ya resolvió el objeto.
        if getattr(self, 'object', None) is not None:
            return self.object
        return super().get_object(queryset)
