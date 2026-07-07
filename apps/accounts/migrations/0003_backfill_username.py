"""Rellena `User.username` como identificador público válido y único.

Los usuarios existentes pueden no tener username, tenerlo en un formato inválido
(p. ej. derivado del email con `@`) o colisionar entre sí sin distinguir
mayúsculas. Esta migración normaliza todo a las reglas de
`apps/accounts/validators.py` garantizando unicidad case-insensitive.

Idempotente: un username ya válido y único se conserva sin cambios.
"""
import re

from django.db import migrations

from apps.accounts.validators import (
    USERNAME_REGEX,
    normalize_username_from_email,
)

_valid = re.compile(USERNAME_REGEX)


def backfill_usernames(apps, schema_editor):
    User = apps.get_model('auth', 'User')

    chosen = []          # usernames finales (case original)
    chosen_lower = set()  # para colisiones case-insensitive

    for user in User.objects.all().order_by('pk'):
        current = user.username or ''
        if _valid.match(current) and current.lower() not in chosen_lower:
            chosen.append(current)
            chosen_lower.add(current.lower())
            continue

        new_username = normalize_username_from_email(user.email, chosen)
        user.username = new_username
        user.save(update_fields=['username'])
        chosen.append(new_username)
        chosen_lower.add(new_username.lower())


def noop_reverse(apps, schema_editor):
    # No se revierte: no hay forma de recuperar el estado previo del username.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_userprofile_bikes_userprofile_bio_userprofile_photo_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_usernames, noop_reverse),
    ]
