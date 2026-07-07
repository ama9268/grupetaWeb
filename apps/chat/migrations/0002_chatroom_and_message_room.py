import django.db.models.deletion
from django.db import migrations, models


def create_general_room(apps, schema_editor):
    ChatRoom = apps.get_model('chat', 'ChatRoom')
    Message = apps.get_model('chat', 'Message')
    general, _ = ChatRoom.objects.get_or_create(
        slug='general',
        defaults={'name': 'General', 'category': 'general'},
    )
    Message.objects.filter(room__isnull=True).update(room=general)


def noop_reverse(apps, schema_editor):
    # La sala general permanece; no se revierte la asignación de mensajes.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChatRoom',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('slug', models.SlugField(max_length=220, unique=True)),
                ('category', models.CharField(
                    choices=[('general', 'General'), ('eventos', 'Eventos')],
                    db_index=True, default='general', max_length=20,
                )),
                ('is_archived', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['created_at']},
        ),
        migrations.RemoveIndex(
            model_name='message',
            name='chat_messag_created_b6b51c_idx',
        ),
        migrations.AddField(
            model_name='message',
            name='room',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='messages',
                to='chat.chatroom',
            ),
        ),
        migrations.RunPython(create_general_room, noop_reverse),
        migrations.AlterField(
            model_name='message',
            name='room',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='messages',
                to='chat.chatroom',
            ),
        ),
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['room', 'created_at'], name='chat_msg_room_created_idx'),
        ),
    ]
