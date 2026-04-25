"""
Base Django settings shared by all environments.
Environment-specific overrides live in development.py / production.py.
"""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError('DJANGO_SECRET_KEY environment variable is required')

# Default closed; environment modules relax this where appropriate.
DEBUG = False
ALLOWED_HOSTS = [h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',') if h.strip()]


LOGIN_URL = '/common/login/'


ENABLE_REST_API = os.environ.get('ENABLE_REST_API', '0').lower() in ('1', 'true', 'yes')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'common',
    'pyddns',
]

if ENABLE_REST_API:
    INSTALLED_APPS += [
        'rest_framework',
        'rest_framework.authtoken',
        'api',
    ]

    REST_FRAMEWORK = {
        'DEFAULT_AUTHENTICATION_CLASSES': [
            'rest_framework.authentication.TokenAuthentication',
            'rest_framework.authentication.SessionAuthentication',
        ],
        'DEFAULT_PERMISSION_CLASSES': [
            'rest_framework.permissions.IsAuthenticated',
        ],
        'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
        'PAGE_SIZE': 20,
    }

MIDDLEWARE = (
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'pyddns.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            'common/templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.request',
                'common.context_processors.site_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'pyddns.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': '5432',
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.RemoteUserBackend',
    'django.contrib.auth.backends.ModelBackend',
)


# Internationalization
#
# DJANGO_LANGUAGE_CODE controls the i18n mode:
#   - empty / unset → international mode: LocaleMiddleware auto-detects from
#     Accept-Language and the user can switch via the language picker. EN
#     is the fallback when nothing matches.
#   - non-empty (e.g. "es", "fr", "pt-br") → locked mode: every page is
#     served in that language. The picker is hidden. Other locale URLs
#     (/de/..., /ja/...) return 404.
_LOCKED = (os.environ.get('DJANGO_LANGUAGE_CODE') or '').strip().lower()
LANGUAGE_LOCKED = bool(_LOCKED)
LANGUAGE_CODE = _LOCKED if LANGUAGE_LOCKED else 'en'
TIME_ZONE = os.environ.get('DJANGO_TIME_ZONE', 'UTC')
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'

DNS_HOST = os.environ.get('DNS_HOST')
DNS_API_PORT = os.environ.get('DNS_API_PORT')
DNS_SHARED_SECRET = os.environ.get('DNS_SHARED_SECRET')
DNS_ALLOW_AGENT = os.environ.get('DNS_ALLOW_AGENT')
DNS_DOMAIN = os.environ.get('DNS_DOMAIN')
OWN_ADMIN = os.environ.get('OWN_ADMIN')


from django.utils.translation import gettext_lazy as _

_ALL_LANGUAGES = (
    ('es', _('Spanish')),
    ('en', _('English')),
    ('pt-br', _('Brazilian Portuguese')),
    ('fr', _('French')),
    ('de', _('German')),
    ('ru', _('Russian')),
    ('ja', _('Japanese')),
    ('zh-hans', _('Simplified Chinese')),
)

if LANGUAGE_LOCKED:
    # Accept exact match first ('es' or 'pt-br'); fall back to the base
    # language part so 'es-es', 'pt-BR', 'fr-FR' all resolve sensibly.
    _matched = [(c, n) for c, n in _ALL_LANGUAGES if c == LANGUAGE_CODE]
    if not _matched:
        _base = LANGUAGE_CODE.split('-')[0]
        _matched = [(c, n) for c, n in _ALL_LANGUAGES if c == _base]
    if not _matched:
        raise RuntimeError(
            f'DJANGO_LANGUAGE_CODE={LANGUAGE_CODE!r} is not a supported locale. '
            f'Supported: {[c for c, _n in _ALL_LANGUAGES]}'
        )
    LANGUAGE_CODE = _matched[0][0]  # canonicalize to the entry's own code
    LANGUAGES = tuple(_matched)
else:
    LANGUAGES = _ALL_LANGUAGES

LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
)

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
