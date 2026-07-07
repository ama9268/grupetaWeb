import django.db.models.deletion
from django.db import migrations, models


def backfill_event_chat_rooms(apps, schema_editor):
    Event = apps.get_model('events', 'Event')
    ChatRoom = apps.get_model('chat', 'ChatRoom')
    for event in Event.objects.filter(chat_room__isnull=True):
        room = ChatRoom.objects.create(
            name=event.title,
            slug=f'evento-{event.pk}',
            category='eventos',
        )
        event.chat_room = room
        event.save(update_fields=['chat_room'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0002_event_states_and_rsvp_rename'),
        ('chat', '0002_chatroom_and_message_room'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='chat_room',
            field=models.OneToOneField(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='event',
                to='chat.chatroom',
            ),
        ),
        migrations.RunPython(backfill_event_chat_rooms, noop_reverse),
    ]
