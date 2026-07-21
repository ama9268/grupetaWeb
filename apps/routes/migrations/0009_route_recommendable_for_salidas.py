from django.db import migrations, models


def backfill_recommendable_for_salidas(apps, schema_editor):
    """Rutas ya enlazadas a un evento que NO es una Salida (viaje/carrera/otro)
    pasan a `False` — mismo criterio que se aplica a partir de ahora al crear
    una ruta nueva desde un evento (ver `apps.events.views._apply_route_selection`).
    El resto (Salidas, o rutas sin evento enlazado) se queda en `True` (default).
    """
    Route = apps.get_model('routes', 'Route')
    Route.objects.filter(events__event_type__in=['viaje', 'carrera', 'otro']).update(
        recommendable_for_salidas=False
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('routes', '0008_route_difficulty'),
    ]

    operations = [
        migrations.AddField(
            model_name='route',
            name='recommendable_for_salidas',
            field=models.BooleanField(
                default=True,
                help_text=(
                    'Desmárcala si es una ruta puntual (p.ej. un viaje lejano) que no '
                    'debe sugerirse para las Salidas habituales de la grupeta.'
                ),
                verbose_name='Recomendable para Salidas',
            ),
        ),
        migrations.RunPython(backfill_recommendable_for_salidas, noop_reverse),
    ]
