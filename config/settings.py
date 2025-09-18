import os
from pathlib import Path
from dotenv import load_dotenv

# 1) Construye la ruta al .env
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / '.env'

# 2) Cárgalo (si existe)
load_dotenv(dotenv_path=env_path)

# 3) Ahora sí puedes usar las variables
ANDREANI_API_KEY = os.getenv('ANDREANI_API_KEY', '')
ANDREANI_API_URL = os.getenv('ANDREANI_API_URL', '')

# Base dir
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-...'
DEBUG = True
ALLOWED_HOSTS = []

# Apps
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'store',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'store' / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
            'store.context_processors.cart_count',
        ],
    },
}]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'es-ar'
TIME_ZONE = 'America/Argentina/Buenos_Aires'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Mercado Pago
MP_ACCESS_TOKEN = os.getenv('MP_ACCESS_TOKEN', 'TU_TOKEN_MERCADOPAGO')
COSTO_ENVIO = 2000
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

print("Andreani key:", ANDREANI_API_KEY[:4], "…")
print("Andreani URL:", ANDREANI_API_URL)
