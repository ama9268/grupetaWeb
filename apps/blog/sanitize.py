import nh3

# Etiquetas permitidas en el HTML del blog (coherentes con lo que produce el editor Quill).
ALLOWED_TAGS = {
    'p', 'br', 'strong', 'b', 'em', 'i', 'u', 's',
    'blockquote', 'pre', 'code',
    'h1', 'h2', 'h3',
    'ol', 'ul', 'li',
    'a', 'img',
}

ALLOWED_ATTRIBUTES = {
    # nh3 gestiona 'rel' automáticamente (link_rel), no debe listarse aquí.
    'a': {'href', 'title', 'target'},
    'img': {'src', 'alt'},
}

ALLOWED_URL_SCHEMES = {'http', 'https', 'mailto'}


def sanitize_html(html):
    """Limpia HTML de contenido de usuario eliminando scripts, handlers y URLs peligrosas.

    Defensa contra XSS almacenado: aunque solo publican miembros aprobados, el contenido
    del blog se muestra con `|safe`, así que se sanea antes de persistirlo.
    """
    if not html:
        return html
    return nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_URL_SCHEMES,
    )
