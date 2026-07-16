import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('routes', '0004_backfill_route_group_and_geom'),
    ]

    operations = [
        migrations.AlterField(
            model_name='route',
            name='group',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='routes', to='groups.group',
            ),
        ),
        migrations.AddIndex(
            model_name='route',
            index=models.Index(fields=['group', 'distance_km'], name='routes_rout_group_i_c964af_idx'),
        ),
    ]
