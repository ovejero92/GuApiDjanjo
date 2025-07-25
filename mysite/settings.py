from pathlib import Path
import os
import environ
import dj_database_url

# ========== 1. CONFIGURACIÓN DE ENTORNO ==========
# Esta es la configuración moderna y recomendada.

BASE_DIR = Path(__file__).resolve().parent.parent

# Inicializa 'environ' para leer variables
env = environ.Env(
    # Define valores por defecto y el tipo de dato.
    # Si no encuentra DEBUG en el .env, será False.
    DEBUG=(bool, False)
)

# Lee el archivo .env si existe (esto solo funcionará en tu PC local)
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))


# ========== 2. VARIABLES CLAVE Y DEBUG ==========

# Lee la SECRET_KEY. Si no la encuentra, dará un error (¡esto es más seguro!).
SECRET_KEY = env('SECRET_KEY')

# 'RENDER' es una variable que existe automáticamente en Render.
# Esto hace que DEBUG sea False en producción y True en local (porque lee DEBUG=True del .env).
IS_PRODUCTION = 'RENDER' in os.environ
DEBUG = not IS_PRODUCTION if IS_PRODUCTION else env('DEBUG')


# ========== 3. CONFIGURACIÓN ESTÁNDAR DE DJANGO ==========

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'turnosok.com', 'www.turnosok.com']

RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'myapp',
    'rest_framework',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = 'mysite.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'mysite.wsgi.application'

DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{os.path.join(BASE_DIR, "db.sqlite3")}',
        conn_max_age=600
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# ========== 4. ARCHIVOS ESTÁTICOS Y MULTIMEDIA ==========

STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ========== 5. CONFIGURACIONES DE SERVICIOS EXTERNOS ==========

# --- EMAIL (SendGrid en producción, Consola en local) ---
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='notificaciones@local.com')
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.sendgrid.net'
    EMAIL_HOST_USER = 'apikey'
    EMAIL_HOST_PASSWORD = env('SENDGRID_API_KEY')
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')

# --- GOOGLE MAPS ---
GOOGLE_MAPS_API_KEY = env('GOOGLE_MAPS_API_KEY')


# ========== 6. CONFIGURACIÓN DE ALLAUTH ==========

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SITE_ID = 1
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_SIGNUP_FORM_CLASS = 'myapp.forms.CustomSignupForm'
SOCIALACCOUNT_SIGNUP_FORM_CLASS = 'myapp.forms.CustomSocialSignupForm'
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'}
    }
}


# ========== 7. CONFIGURACIÓN DE SEGURIDAD PARA PRODUCCIÓN ==========
if IS_PRODUCTION:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
if IS_PRODUCTION:
    # --- En Producción (Render), usamos AWS S3 ---
    AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    
    # Le decimos a Django que use django-storages para los archivos subidos (media)
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        },
        "staticfiles": { # Whitenoise sigue manejando los estáticos
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
    
    # La URL base para los archivos multimedia ahora apuntará a S3
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"

else:
    # --- En Local, seguimos usando el disco duro ---
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
    
# ========== 8. CONFIGURACIÓN DE LOGGING PARA PRODUCCIÓN ==========
# Esto fuerza a Django a mostrar los errores en los logs de Render.

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO", # Cambia a "DEBUG" para ver aún más detalle si es necesario
    },
}