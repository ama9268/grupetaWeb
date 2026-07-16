import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('media_gallery', '0001_initial'),
        ('groups', '0002_create_default_group'),
    ]

    operations = [
        migrations.AddField(
            model_name='album',
            name='group',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name='albums', to='groups.group',
            ),
        ),
        migrations.AddField(
            model_name='mediaitem',
            name='group',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name='media_items', to='groups.group',
            ),
        ),
        migrations.AddIndex(
            model_name='mediaitem',
            index=models.Index(fields=['group', '-created_at'], name='media_item_group_created_idx'),
        ),
    ]
