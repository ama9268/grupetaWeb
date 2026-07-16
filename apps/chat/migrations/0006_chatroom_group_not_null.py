import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0005_backfill_chatroom_group'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chatroom',
            name='group',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='chat_rooms', to='groups.group',
            ),
        ),
    ]
