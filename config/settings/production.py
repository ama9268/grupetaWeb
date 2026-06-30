from .base import *

DEBUG = False

DATABASES = {
    'default': env.db('DATABASE_URL')
}

ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS')

STORAGES = {
    'default': {
        'BACKEND': 'cloudinary_storage.storage.MediaCloudinaryStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# Canales Redis en producción
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [env('REDIS_URL', default='redis://redis:6379/0')],
        },
    }
}

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Traefik termina el SSL y reenvía HTTP interno a Django.
# Esta cabecera le dice a Django que la petición original era HTTPS.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# No redirigir a HTTPS desde Django: Traefik ya lo hace externamente.
SECURE_SSL_REDIRECT = False

# Necesario para que los formularios POST funcionen con HTTPS tras Traefik.
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])
