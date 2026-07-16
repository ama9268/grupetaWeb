import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('media_gallery', '0003_backfill_group'),
    ]

    operations = [
        migrations.AlterField(
            model_name='album',
            name='group',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='albums', to='groups.group',
            ),
        ),
        migrations.AlterField(
            model_name='mediaitem',
            name='group',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='media_items', to='groups.group',
            ),
        ),
    ]
