import django.contrib.gis.db.models.fields
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0002_create_default_group'),
        ('routes', '0002_enable_postgis'),
    ]

    operations = [
        migrations.AddField(
            model_name='route',
            name='group',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name='routes', to='groups.group',
            ),
        ),
        migrations.AlterField(
            model_name='route',
            name='gpx_file',
            field=models.FileField(blank=True, upload_to='gpx/'),
        ),
        migrations.AddField(
            model_name='route',
            name='track_geom',
            field=django.contrib.gis.db.models.fields.LineStringField(
                blank=True, geography=True, null=True, srid=4326,
            ),
        ),
        migrations.AddField(
            model_name='route',
            name='start_point',
            field=django.contrib.gis.db.models.fields.PointField(
                blank=True, geography=True, null=True, srid=4326,
            ),
        ),
    ]
