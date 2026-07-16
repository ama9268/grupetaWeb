from django.db import migrations

from apps.groups.constants import DEFAULT_GROUP_SLUG


def backfill_group(apps, schema_editor):
    Post = apps.get_model('blog', 'Post')
    Group = apps.get_model('groups', 'Group')
    default_group = Group.objects.get(slug=DEFAULT_GROUP_SLUG)
    Post.objects.filter(group__isnull=True).update(group=default_group)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0003_post_group_nullable'),
    ]

    operations = [
        migrations.RunPython(backfill_group, noop_reverse),
    ]
