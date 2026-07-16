from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('routes', '0005_route_group_not_null'),
    ]

    operations = [
        migrations.AddField(
            model_name='route',
            name='strava_activity_id',
            field=models.BigIntegerField(blank=True, null=True, unique=True),
        ),
    ]
