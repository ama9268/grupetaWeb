"""Validación y normalización del `username` público.

El `username` es el identificador público visible de un usuario (el login sigue
siendo por email). Reglas: letras, dígitos, `.`, `_`, `-`; sin espacios; longitud
3–30. Unicidad case-insensitive (se valida en los formularios).

Este módulo es la fuente única de verdad del formato: lo reutilizan el signup de
allauth (`ACCOUNT_USERNAME_VALIDATORS`), el formulario de perfil de `members` y la
data migration de backfill.
"""
import re

from django.core.validators import RegexValidator

USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 30

USERNAME_REGEX = r'^[a-zA-Z0-9._-]{%d,%d}$' % (USERNAME_MIN_LENGTH, USERNAME_MAX_LENGTH)

username_regex_validator = RegexValidator(
    regex=USERNAME_REGEX,
    message=(
        'El nombre de usuario debe tener entre 3 y 30 caracteres y solo admite '
        'letras, dígitos y los símbolos . _ -'
    ),
)

# Lista consumida por allauth vía ACCOUNT_USERNAME_VALIDATORS.
username_validators = [username_regex_validator]

# Caracteres no permitidos, para limpiar al derivar un username automáticamente.
_INVALID_CHARS = re.compile(r'[^a-z0-9._-]')


def normalize_username_from_email(email, taken):
    """Deriva un `username` válido y único a partir de un email.

    - Toma el *local-part* (antes de la `@`), lo pasa a minúsculas y elimina
      caracteres no permitidos.
    - Garantiza la longitud mínima y máxima.
    - Desambigua colisiones (case-insensitive) con sufijo numérico: `ana`, `ana2`…

    `taken` es un iterable de usernames ya usados; la comparación es
    case-insensitive. Devuelve el username elegido (no muta `taken`).
    """
    taken_lower = {u.lower() for u in taken if u}

    local = (email or '').split('@')[0].lower()
    base = _INVALID_CHARS.sub('', local)
    if len(base) < USERNAME_MIN_LENGTH:
        # Relleno estable para locales demasiado cortos o vacíos.
        base = (base + 'miembro')[:USERNAME_MAX_LENGTH]
    base = base[:USERNAME_MAX_LENGTH]

    candidate = base
    suffix = 1
    while candidate.lower() in taken_lower:
        suffix += 1
        tail = str(suffix)
        candidate = base[:USERNAME_MAX_LENGTH - len(tail)] + tail

    return candidate
