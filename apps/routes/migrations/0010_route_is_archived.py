from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('routes', '0009_route_recommendable_for_salidas'),
    ]

    operations = [
        migrations.AddField(
            model_name='route',
            name='is_archived',
            field=models.BooleanField(
                default=False,
                help_text=(
                    'Una ruta archivada desaparece del catálogo y de las recomendaciones de '
                    'Salidas, pero se conserva (no se puede eliminar una ruta que ya ha '
                    'participado en algún evento/Salida, para no perder su historial).'
                ),
                verbose_name='Archivada',
            ),
        ),
    ]
