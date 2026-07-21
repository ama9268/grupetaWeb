from django.db import migrations, models


def backfill_difficulty(apps, schema_editor):
    Route = apps.get_model('routes', 'Route')
    Route.objects.filter(elevation_gain_m__gte=1500).update(difficulty='dura')
    Route.objects.filter(elevation_gain_m__gte=700, elevation_gain_m__lt=1500).update(difficulty='media')
    Route.objects.filter(elevation_gain_m__isnull=False, elevation_gain_m__lt=700).update(difficulty='suave')


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('routes', '0007_stravaaccount_stravaimportcandidate'),
    ]

    operations = [
        migrations.AddField(
            model_name='route',
            name='difficulty',
            field=models.CharField(
                blank=True, max_length=10,
                choices=[('suave', 'Suave'), ('media', 'Media'), ('dura', 'Dura')],
            ),
        ),
        migrations.RunPython(backfill_difficulty, noop_reverse),
    ]
