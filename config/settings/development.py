from .base import *

DEBUG = True

INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
INTERNAL_IPS = ['127.0.0.1']

DATABASES = {
    'default': env.db('DATABASE_URL'),
}
# Backend con soporte GeoDjango/PostGIS (apps.routes usa LineStringField/PointField).
DATABASES['default']['ENGINE'] = 'django.contrib.gis.db.backends.postgis'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'mediafiles'

# Mismo backend Pub/Sub que producción (ver nota en production.py) para que
# el comportamiento del chat sea idéntico en local y en el VPS.
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.pubsub.RedisPubSubChannelLayer',
        'CONFIG': {
            'hosts': [env('REDIS_URL', default='redis://localhost:6379/0')],
        },
    }
}
