from django.db import migrations, models


def forwards_rsvp_responses(apps, schema_editor):
    EventRSVP = apps.get_model('events', 'EventRSVP')
    EventRSVP.objects.filter(response='attending').update(response='si')
    EventRSVP.objects.filter(response='not_attending').update(response='no')


def backwards_rsvp_responses(apps, schema_editor):
    EventRSVP = apps.get_model('events', 'EventRSVP')
    EventRSVP.objects.filter(response='si').update(response='attending')
    EventRSVP.objects.filter(response='no').update(response='not_attending')
    # 'quizas' no tiene equivalente en el esquema antiguo; se aproxima a 'not_attending'.
    EventRSVP.objects.filter(response='quizas').update(response='not_attending')


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0001_initial'),
    ]

    operations = [
        # --- Índice antiguo sobre 'date' ---
        migrations.RemoveIndex(
            model_name='event',
            name='events_even_date_5e8e1c_idx',
        ),
        # --- Renombrados que preservan datos ---
        migrations.RenameField(
            model_name='event',
            old_name='date',
            new_name='start_at',
        ),
        migrations.RenameField(
            model_name='eventrsvp',
            old_name='user',
            new_name='member',
        ),
        migrations.AlterUniqueTogether(
            name='eventrsvp',
            unique_together={('event', 'member')},
        ),
        # --- Campos nuevos de Event ---
        migrations.AddField(
            model_name='event',
            name='event_type',
            field=models.CharField(
                choices=[
                    ('ruta_especial', 'Ruta especial'),
                    ('viaje', 'Viaje'),
                    ('carrera', 'Carrera'),
                    ('otro', 'Otro'),
                ],
                default='otro',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='event',
            name='image_public_id',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='event',
            name='image_url',
            field=models.URLField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name='event',
            name='state',
            field=models.CharField(
                choices=[
                    ('pendiente', 'Pendiente'),
                    ('aceptado', 'Aceptado'),
                    ('realizado', 'Realizado'),
                    ('superado', 'Superado'),
                    ('cancelado', 'Cancelado'),
                ],
                default='pendiente',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='event',
            name='is_archived',
            field=models.BooleanField(default=False),
        ),
        # --- Nuevas choices de response + migración de datos ---
        migrations.AlterField(
            model_name='eventrsvp',
            name='response',
            field=models.CharField(
                choices=[('si', 'Voy'), ('no', 'No voy'), ('quizas', 'Quizás')],
                max_length=20,
            ),
        ),
        migrations.RunPython(forwards_rsvp_responses, backwards_rsvp_responses),
        # --- Opciones e índices nuevos ---
        migrations.AlterModelOptions(
            name='event',
            options={'ordering': ['start_at']},
        ),
        migrations.AddIndex(
            model_name='event',
            index=models.Index(fields=['start_at'], name='events_event_start_at_idx'),
        ),
        migrations.AddIndex(
            model_name='event',
            index=models.Index(fields=['state'], name='events_event_state_idx'),
        ),
    ]
