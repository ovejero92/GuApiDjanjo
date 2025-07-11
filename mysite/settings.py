"""
Django settings for mysite project.

Generated by 'django-admin startproject' using Django 5.2.3.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

from pathlib import Path
import os
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY',default='your secret key')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = 'RENDER' not in os.environ
# DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 't')
# DEBUG = True

ALLOWED_HOSTS = ['guapidjanjo.onrender.com', 'localhost', '127.0.0.1']

RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Apps de Terceros (Allauth)
    'django.contrib.sites', # Requerido por allauth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',

    # Tus Apps
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
    "allauth.account.middleware.AccountMiddleware", # Middleware de Allauth
]

ROOT_URLCONF = 'mysite.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')], # Directorio de plantillas a nivel de proyecto
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # 'allauth' necesita este context processor para funcionar bien
                'django.template.context_processors.request',
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

LANGUAGE_CODE = 'es-es' # Cambiado a español
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ==============================================================================
# CONFIGURACIÓN DE EMAIL (SEPARADA PARA LOCAL Y PRODUCCIÓN)
# ==============================================================================
if DEBUG:
    # --- EN LOCAL (DESARROLLO) ---
    # Los correos no se envían, se imprimen en la consola donde ejecutas 'runserver'.
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = 'desarrollo-local@turnosonline.com'
else:
    # --- EN PRODUCCIÓN (RENDER) ---
    # Aquí usaríamos un servicio real como SendGrid.
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.sendgrid.net'
    EMAIL_HOST_USER = 'apikey'  # Esto es literal, la palabra 'apikey'
    EMAIL_HOST_PASSWORD = os.environ.get('SENDGRID_API_KEY', '') # Tu API Key de SendGrid
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    DEFAULT_FROM_EMAIL = 'casti.india@gmail.com' # Un email verificado en SendGrid


# ==============================================================================
# CONFIGURACIÓN DE DJANGO-ALLAUTH
# ==============================================================================
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SITE_ID = 1

# --- Flujo de Autenticación Principal ---
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# --- Configuración de la Cuenta (Registro/Login Normal) ---
ACCOUNT_AUTHENTICATION_METHOD = 'email'       # Los usuarios se loguean con su email.
ACCOUNT_EMAIL_REQUIRED = True                 # El email es obligatorio.
ACCOUNT_USERNAME_REQUIRED = False             # No pedimos un username aparte del email.
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'      # Se requiere verificación de email para poder loguearse.
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = True    # Pide confirmar la contraseña.
ACCOUNT_SESSION_REMEMBER = True               # Opción de "Recordarme".
ACCOUNT_UNIQUE_EMAIL = True                   # Asegura que cada email sea único.

# --- Formularios Personalizados ---
# Le decimos a allauth qué formularios usar para cada flujo.
ACCOUNT_SIGNUP_FORM_CLASS = 'myapp.forms.CustomSignupForm'
SOCIALACCOUNT_SIGNUP_FORM_CLASS = 'myapp.forms.CustomSocialSignupForm'

# --- Configuración de Cuentas Sociales (Google) ---
SOCIALACCOUNT_AUTO_SIGNUP = True              # Si viene de Google con datos válidos, se registra automáticamente.
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'     # Confiamos en que el email de Google está verificado.
SOCIALACCOUNT_LOGIN_ON_GET = True             # Omite la página intermedia de "Continuar con Google".

# --- Proveedores Sociales ---
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        }
    }
}