import django.contrib.gis.db.models.fields
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('routes', '0006_route_strava_activity_id'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='StravaAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('access_token_encrypted', models.TextField()),
                ('refresh_token_encrypted', models.TextField()),
                ('expires_at', models.DateTimeField()),
                ('strava_athlete_id', models.BigIntegerField(unique=True)),
                ('connected_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE, related_name='strava_account',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
        migrations.CreateModel(
            name='StravaImportCandidate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('strava_activity_id', models.BigIntegerField(unique=True)),
                ('name', models.CharField(max_length=200)),
                ('distance_km', models.DecimalField(decimal_places=2, max_digits=6)),
                ('elevation_gain_m', models.IntegerField(blank=True, null=True)),
                ('moving_time_s', models.IntegerField(blank=True, null=True)),
                ('sport_type', models.CharField(blank=True, max_length=50)),
                ('start_point', django.contrib.gis.db.models.fields.PointField(
                    blank=True, geography=True, null=True, srid=4326,
                )),
                ('started_at', models.DateTimeField()),
                ('status', models.CharField(
                    choices=[('pendiente', 'Pendiente'), ('importado', 'Importado'), ('descartado', 'Descartado')],
                    default='pendiente', max_length=20,
                )),
                ('staged_at', models.DateTimeField(auto_now_add=True)),
                ('account', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name='candidates',
                    to='routes.stravaaccount',
                )),
                ('imported_route', models.ForeignKey(
                    on_delete=django.db.models.deletion.SET_NULL, null=True, blank=True,
                    related_name='strava_candidate', to='routes.route',
                )),
            ],
            options={
                'ordering': ['-started_at'],
            },
        ),
        migrations.AddIndex(
            model_name='stravaimportcandidate',
            index=models.Index(fields=['account', 'status'], name='routes_stra_account_06380a_idx'),
        ),
    ]
