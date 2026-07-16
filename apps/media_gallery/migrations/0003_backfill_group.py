from django.db import migrations

from apps.groups.constants import DEFAULT_GROUP_SLUG


def backfill_group(apps, schema_editor):
    Album = apps.get_model('media_gallery', 'Album')
    MediaItem = apps.get_model('media_gallery', 'MediaItem')
    Group = apps.get_model('groups', 'Group')
    default_group = Group.objects.get(slug=DEFAULT_GROUP_SLUG)

    # Álbum ligado a un evento: hereda su grupeta. Álbum suelto: grupeta por defecto.
    for album in Album.objects.filter(group__isnull=True).select_related('event'):
        album.group = album.event.group if album.event_id else default_group
        album.save(update_fields=['group'])

    # Media ligada a un álbum: hereda su grupeta. Media suelta: grupeta por defecto.
    for item in MediaItem.objects.filter(group__isnull=True).select_related('album'):
        item.group = item.album.group if item.album_id else default_group
        item.save(update_fields=['group'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('media_gallery', '0002_group_nullable'),
        ('events', '0006_event_group_not_null'),
    ]

    operations = [
        migrations.RunPython(backfill_group, noop_reverse),
    ]
