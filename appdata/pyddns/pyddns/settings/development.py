"""Development settings: permissive defaults for local work."""

import os

from .base import *  # noqa: F401,F403

DEBUG = os.environ.get('DJANGO_DEBUG', '1').lower() in ('1', 'true', 'yes')

if not ALLOWED_HOSTS:  # noqa: F405
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']
