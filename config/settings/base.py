from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('DJANGO_SECRET_KEY')

ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

SITE_URL = env('SITE_URL', default='http://localhost:8000')

DJANGO_APPS = [
    # 'daphne' debe ir la PRIMERA para que `runserver` sirva ASGI/WebSockets
    # en local (Channels 4.x). Sin ella, runserver arranca en modo WSGI y
    # rechaza el handshake del WebSocket -> el chat marca "Desconectado".
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.gis',
]

THIRD_PARTY_APPS = [
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'channels',
    'storages',
    'cloudinary',
    'cloudinary_storage',
]

LOCAL_APPS = [
    'apps.groups',
    'apps.accounts',
    'apps.members',
    'apps.dashboard',
    'apps.routes',
    'apps.events',
    'apps.blog',
    'apps.media_gallery',
    'apps.chat',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.groups.context_processors.active_group',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es'
TIME_ZONE = 'Europe/Madrid'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SITE_ID = 1

# django-allauth
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ACCOUNT_ADAPTER = 'apps.accounts.adapters.AccountAdapter'
ACCOUNT_FORMS = {'signup': 'apps.accounts.forms.GroupSignupForm'}
ACCOUNT_LOGIN_METHODS = {'email'}
# El login sigue siendo por email; `username` es el identificador público visible.
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_USERNAME_VALIDATORS = 'apps.accounts.validators.username_validators'
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_SIGNUP_REDIRECT_URL = '/accounts/pending/'
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Email
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='grupetaweb@gmail.com')

# Cloudinary
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': env('CLOUDINARY_CLOUD_NAME', default=''),
    'API_KEY': env('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': env('CLOUDINARY_API_SECRET', default=''),
}

# Límites de subida de media (bytes). Ajustables según el plan de Cloudinary.
MAX_IMAGE_UPLOAD_SIZE = env.int('MAX_IMAGE_UPLOAD_SIZE', default=10 * 1024 * 1024)   # 10 MB
MAX_VIDEO_UPLOAD_SIZE = env.int('MAX_VIDEO_UPLOAD_SIZE', default=100 * 1024 * 1024)  # 100 MB

# Strava (import de rutas en apps.routes)
STRAVA_CLIENT_ID = env('STRAVA_CLIENT_ID', default='')
STRAVA_CLIENT_SECRET = env('STRAVA_CLIENT_SECRET', default='')
STRAVA_REDIRECT_URI = env('STRAVA_REDIRECT_URI', default='http://127.0.0.1:8000/routes/strava/callback/')
STRAVA_ENCRYPTION_KEY = env('STRAVA_ENCRYPTION_KEY', default='')

# Agente de recomendación de ruta de Salidas (apps.events.recommender) — ver
# apps/events/CLAUDE.md, sección "Salidas". Todo con default='' / valores neutros para
# que el repo arranque limpio sin ninguna clave configurada.
OPEN_METEO_BASE_URL = env('OPEN_METEO_BASE_URL', default='https://api.open-meteo.com/v1/forecast')
ROUTE_RECOMMENDER_AVG_SPEED_KMH = env.float('ROUTE_RECOMMENDER_AVG_SPEED_KMH', default=22.0)
ROUTE_RECOMMENDER_DISTANCE_TOLERANCE = env.float('ROUTE_RECOMMENDER_DISTANCE_TOLERANCE', default=0.15)
ROUTE_RECOMMENDER_ELEVATION_TOLERANCE = env.float('ROUTE_RECOMMENDER_ELEVATION_TOLERANCE', default=0.25)
ROUTE_RECOMMENDER_MAX_CANDIDATES = env.int('ROUTE_RECOMMENDER_MAX_CANDIDATES', default=5)
ROUTE_RECOMMENDER_HTTP_TIMEOUT_S = env.float('ROUTE_RECOMMENDER_HTTP_TIMEOUT_S', default=5.0)
ROUTE_RECOMMENDER_MAX_TRACK_POINTS = env.int('ROUTE_RECOMMENDER_MAX_TRACK_POINTS', default=200)

# 'anthropic' | 'ollama' | 'none' — sin ninguno configurado por defecto.
ROUTE_RECOMMENDER_LLM_PROVIDER = env('ROUTE_RECOMMENDER_LLM_PROVIDER', default='none')
ANTHROPIC_API_KEY = env('ANTHROPIC_API_KEY', default='')
ANTHROPIC_MODEL = env('ANTHROPIC_MODEL', default='claude-haiku-4-5')
OLLAMA_BASE_URL = env('OLLAMA_BASE_URL', default='http://127.0.0.1:11434')
OLLAMA_MODEL = env('OLLAMA_MODEL', default='llama3.1')
LLM_TIMEOUT_S = env.float('LLM_TIMEOUT_S', default=12.0)

