"""Serialización única de mensajes de chat.

La usan tanto el consumer WebSocket (`consumers.py`) como la vista HTTP de
subida de adjuntos (`views.py`), para que el JSON que llega al cliente tenga
siempre la misma forma independientemente del origen.
"""


def serialize_message(msg):
    return {
        'id': msg.pk,
        # Identificador público = username (nunca el email).
        'user': msg.user.username or 'Miembro',
        'content': msg.content,
        'timestamp': msg.created_at.strftime('%d/%m/%Y %H:%M'),
        # Vacíos ('' / None) en mensajes de solo texto.
        'attachment_type': msg.attachment_type or None,
        'attachment_url': msg.attachment_url or None,
    }
