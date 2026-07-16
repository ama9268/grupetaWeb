import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0003_event_chat_room'),
        ('groups', '0002_create_default_group'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='group',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name='events', to='groups.group',
            ),
        ),
        migrations.AddIndex(
            model_name='event',
            index=models.Index(fields=['group', 'start_at'], name='events_event_group_start_idx'),
        ),
    ]
