from django.db import models


class GroupScopedQuerySet(models.QuerySet):
    """QuerySet base para modelos acotados por grupeta (Event, ChatRoom, Post, Album, MediaItem).

    Se usa sobre todo para agregaciones combinadas (dashboard), donde interesa el
    contenido de TODAS las grupetas del usuario a la vez. Las páginas de "grupeta
    activa" filtran directamente por `.filter(group=active_group)`.
    """

    group_field = 'group'

    def for_user(self, user):
        profile = getattr(user, 'profile', None)
        if profile is None:
            return self.none()
        if profile.is_admin:
            return self
        return self.filter(**{f'{self.group_field}__in': profile.approved_groups()})

    def moderated_by(self, user):
        profile = getattr(user, 'profile', None)
        if profile is None:
            return self.none()
        if profile.is_admin:
            return self
        return self.filter(**{f'{self.group_field}__in': profile.moderated_groups()})
