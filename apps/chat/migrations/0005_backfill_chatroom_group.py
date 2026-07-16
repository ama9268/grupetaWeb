from django.db import migrations

from apps.groups.constants import DEFAULT_GROUP_SLUG


def backfill_group(apps, schema_editor):
    ChatRoom = apps.get_model('chat', 'ChatRoom')
    Group = apps.get_model('groups', 'Group')
    default_group = Group.objects.get(slug=DEFAULT_GROUP_SLUG)
    ChatRoom.objects.filter(group__isnull=True).update(group=default_group)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0004_chatroom_group_nullable'),
    ]

    operations = [
        migrations.RunPython(backfill_group, noop_reverse),
    ]
