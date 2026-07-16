from apps.accounts.models import UserProfile
from apps.groups.models import Membership


def members_visible_to(user):
    """Miembros con los que `user` comparte al menos una grupeta aprobada
    (todos los miembros de la plataforma si es Admin global). Usado por el
    Dashboard (vista combinada) y por el propio directorio de `members`."""
    profile = user.profile
    if profile.is_admin:
        return UserProfile.objects.filter(
            user__memberships__status=Membership.Status.APPROVED
        ).distinct()
    return UserProfile.objects.filter(
        user__memberships__group__in=profile.approved_groups(),
        user__memberships__status=Membership.Status.APPROVED,
    ).distinct()
