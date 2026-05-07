from pathlib import Path
import os
import environ
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False)
)

environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY')
IS_PRODUCTION = 'RENDER' in os.environ
DEBUG = not IS_PRODUCTION if IS_PRODUCTION else env('DEBUG')

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'turnosok.com', 'www.turnosok.com']
ALLOWED_HOSTS.append(".onrender.com")

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
    'django.contrib.sitemaps',
    'anymail',
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
        default=os.getenv('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True,
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
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Correo: en Render «free» están bloqueados los puertos SMTP (25/465/587) — usar HTTPS vía SendGrid si hay SENDGRID_API_KEY.
SENDGRID_API_KEY = env('SENDGRID_API_KEY', default='')

if SENDGRID_API_KEY:
    EMAIL_BACKEND = 'anymail.backends.sendgrid.EmailBackend'
    ANYMAIL = {'SENDGRID_API_KEY': SENDGRID_API_KEY}
    DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@turnosok.com')
elif DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='notificaciones@local.com')
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
    EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
    EMAIL_PORT = env.int('EMAIL_PORT', default=587)
    EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
    EMAIL_TIMEOUT = env.int('EMAIL_TIMEOUT', default=15)
    DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER)

GOOGLE_MAPS_API_KEY = env('GOOGLE_MAPS_API_KEY')

MERCADOPAGO_ACCESS_TOKEN = env('MERCADOPAGO_ACCESS_TOKEN')

ACCOUNT_ADAPTER = 'myapp.adapters.MyAccountAdapter'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SITE_ID = 1
LOGOUT_REDIRECT_URL = '/'
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = True
# Sin login automático tras registro: el usuario entra recién tras verificar email (flujo Pidgeon).
ACCOUNT_LOGIN_ON_SIGNUP = False
ACCOUNT_FORMS = {
    'login': 'myapp.forms.CustomLoginForm',
}
# Verificación por correo (allauth): 'none' | 'optional' | 'mandatory'
# Por defecto 'none': el usuario queda activo y puede iniciar sesión sin enlace.
# Para reactivar el flujo con correo: 'mandatory' + envío real (SMTP en host que lo
# permita o SENDGRID_API_KEY; en Render free el SMTP saliente está bloqueado).
_allowed_email_verification = frozenset({'none', 'optional', 'mandatory'})
_raw_email_verification = env('ACCOUNT_EMAIL_VERIFICATION', default='none')
ACCOUNT_EMAIL_VERIFICATION = (
    _raw_email_verification
    if _raw_email_verification in _allowed_email_verification
    else 'none'
)
# Rechaza dominios de correo temporal listados en myapp/signup_email_policy.py
BLOCK_DISPOSABLE_SIGNUP_EMAILS = env.bool('BLOCK_DISPOSABLE_SIGNUP_EMAILS', default=True)
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_SIGNUP_FORM_CLASS = 'myapp.forms.CustomSignupForm'
ACCOUNT_SIGNUP_REDIRECT_URL = '/accounts/login/'
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

# Pidgeon (API HTTPS) — envío con fallback en EmailFailureLog (ver myapp/email_service.py).
PIDGEON_URL = env('PIDGEON_URL', default='https://pidgeon-1.onrender.com')
PIDGEON_TIMEOUT = env.float('PIDGEON_TIMEOUT', default=25.0)
SITE_BASE_URL = env('SITE_BASE_URL', default='https://turnosok.com')
# Secreto para POST /internal/cron/send-reminders/ (cron gratuito p. ej. cron-job.org).
REMINDER_CRON_SECRET = env('REMINDER_CRON_SECRET', default='')


if IS_PRODUCTION:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
if IS_PRODUCTION:
    AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
    
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"

else:
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

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
        "level": "INFO",
    },
}