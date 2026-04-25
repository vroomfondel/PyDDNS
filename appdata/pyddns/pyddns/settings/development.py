"""Development settings: permissive defaults for local work."""

import os

from .base import *  # noqa: F401,F403

DEBUG = os.environ.get('DJANGO_DEBUG', '1').lower() in ('1', 'true', 'yes')

if not ALLOWED_HOSTS:  # noqa: F405
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# Trust both http and https variants of dev hosts so CSRF passes regardless
# of whether you hit nginx (HTTPS) or runserver directly (HTTP).
CSRF_TRUSTED_ORIGINS = []
for _h in ALLOWED_HOSTS:  # noqa: F405
    if _h and _h != '*':
        CSRF_TRUSTED_ORIGINS += [f'http://{_h}', f'https://{_h}']
