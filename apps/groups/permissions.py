from django.core.exceptions import PermissionDenied


def user_is_group_moderator(user, group):
    profile = getattr(user, 'profile', None)
    return bool(profile) and profile.is_group_moderator(group)


def user_is_group_member(user, group):
    profile = getattr(user, 'profile', None)
    return bool(profile) and profile.is_member_of(group)


def require_group_moderator(user, group):
    if not user_is_group_moderator(user, group):
        raise PermissionDenied


def require_group_member(user, group):
    if not user_is_group_member(user, group):
        raise PermissionDenied
