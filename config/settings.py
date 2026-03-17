import sys
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Add apps directory to Python path
sys.path.insert(0, str(BASE_DIR / 'apps'))

# IMPORTANT: Set custom user model FIRST
AUTH_USER_MODEL = 'users.User'

# Quick-start development settings
SECRET_KEY = 'django-insecure-q6ovbtmncxx0$3kr-175^s^l4kmo8h#0xzr^+)d=9j-claz_ek'
DEBUG = True
ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'daphne',  # ASGI server (before django)
    # Django built-in apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'corsheaders',
    'crispy_forms',
    'crispy_bootstrap5',
    
    # Custom apps - IMPORTANT: users must come first
    'apps.users',
    'apps.authentication',
    'apps.verification',
    'apps.core',
    'apps.api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.authentication.middleware.RateLimitMiddleware',
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
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database: use DATABASE_URL from .env (e.g. Neon PostgreSQL) or fallback to SQLite
DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
if DATABASE_URL and not DATABASE_URL.startswith('sqlite'):
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Cache (for test KYC background job status / live log)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'OPTIONS': {'MAX_ENTRIES': 500},
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (WhiteNoise serves these in production from STATIC_ROOT)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# Media files: local by default; Backblaze B2 when AWS_* env vars are set (sensitive KYC IDs)
MEDIA_ROOT = BASE_DIR / 'media'
_use_b2 = bool(os.environ.get('AWS_STORAGE_BUCKET_NAME') and os.environ.get('AWS_ACCESS_KEY_ID') and os.environ.get('AWS_SECRET_ACCESS_KEY'))
if _use_b2:
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_ENDPOINT_URL = os.environ.get('AWS_S3_ENDPOINT_URL', 'https://s3.eu-central-003.backblazeb2.com')
    AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'eu-central-003')
    # Private bucket: signed URLs only (no public access)
    AWS_QUERYSTRING_AUTH = True
    AWS_QUERYSTRING_EXPIRE = 3600
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    # Server-Side Encryption for sensitive KYC documents
    AWS_S3_OBJECT_PARAMETERS = {'ServerSideEncryption': 'AES256'}
    AWS_DEFAULT_ACL = 'private'
    AWS_S3_FILE_OVERWRITE = False
    MEDIA_URL = '/media/'
    # Django 4.2+ uses STORAGES for default_storage; DEFAULT_FILE_STORAGE is ignored
    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
        },
    }
else:
    MEDIA_URL = '/media/'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS settings
CORS_ALLOW_ALL_ORIGINS = True

# CSRF: allow same-origin requests from the deployed host (Django 4+ checks Origin)
_origins = os.environ.get('CSRF_TRUSTED_ORIGINS', 'https://kyc-service-au1k.onrender.com').strip()
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _origins.split(',') if o.strip()]

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'apps.api.authentication.APIKeyAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'UNAUTHENTICATED_USER': None, 
}

# Login URLs (use URL name so admin/staff redirects resolve; name is auth:login)
LOGIN_URL = 'auth:login'
LOGIN_REDIRECT_URL = 'user:dashboard'