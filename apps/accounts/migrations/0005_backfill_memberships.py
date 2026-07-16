from django.db import migrations

from apps.groups.constants import DEFAULT_GROUP_SLUG


def backfill_memberships(apps, schema_editor):
    # Modelos históricos (apps.get_model), NUNCA el import real: ver la nota en
    # apps/groups/migrations/0002_create_default_group.py sobre por qué los
    # signals conectados al modelo real no deben dispararse aquí.
    UserProfile = apps.get_model('accounts', 'UserProfile')
    Group = apps.get_model('groups', 'Group')
    Membership = apps.get_model('groups', 'Membership')

    default_group = Group.objects.get(slug=DEFAULT_GROUP_SLUG)

    for profile in UserProfile.objects.all():
        is_admin = profile.role == 'admin'
        membership_role = 'moderator' if profile.role in ('admin', 'moderator') else 'member'

        if is_admin:
            profile.is_admin = True
            profile.save(update_fields=['is_admin'])

        Membership.objects.get_or_create(
            user_id=profile.user_id,
            group=default_group,
            defaults={
                'role': membership_role,
                'status': profile.status,
                'created_at': profile.created_at,
            },
        )


def noop_reverse(apps, schema_editor):
    # No se deshace: quitar el backfill dejaría usuarios existentes sin ninguna
    # grupeta ni rol, bloqueándolos por completo.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_userprofile_is_admin'),
        ('groups', '0002_create_default_group'),
    ]

    operations = [
        migrations.RunPython(backfill_memberships, noop_reverse),
    ]
