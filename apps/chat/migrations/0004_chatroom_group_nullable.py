import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0003_message_attachment_public_id_message_attachment_type_and_more'),
        ('groups', '0002_create_default_group'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatroom',
            name='group',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name='chat_rooms', to='groups.group',
            ),
        ),
        migrations.AddIndex(
            model_name='chatroom',
            index=models.Index(fields=['group', 'category'], name='chat_room_group_category_idx'),
        ),
    ]
