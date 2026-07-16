from django.db import migrations

from apps.groups.constants import DEFAULT_GROUP_NAME, DEFAULT_GROUP_SLUG


def create_default_group(apps, schema_editor):
    # Usar SIEMPRE el modelo histórico (apps.get_model) en data migrations: el
    # modelo real de apps/groups/models.py puede llevar conectados signals
    # (p.ej. autocreación de la ChatRoom "general" de la grupeta) que asumen
    # columnas de otras apps que en este punto de la secuencia de migraciones
    # aún no existen.
    Group = apps.get_model('groups', 'Group')
    Group.objects.get_or_create(
        slug=DEFAULT_GROUP_SLUG,
        defaults={'name': DEFAULT_GROUP_NAME, 'is_active': True},
    )


def remove_default_group(apps, schema_editor):
    Group = apps.get_model('groups', 'Group')
    Group.objects.filter(slug=DEFAULT_GROUP_SLUG).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_group, remove_default_group),
    ]
