"""Test environment defaults and shared fixtures."""
import os

# Force development settings for tests, regardless of what the container's
# environment defines (production triggers SECURE_SSL_REDIRECT, HSTS, etc.,
# which break Django's plain-HTTP test client).
os.environ['DJANGO_SETTINGS_MODULE'] = 'pyddns.settings.development'

os.environ.setdefault('DJANGO_SECRET_KEY', 'test-secret-key-not-for-production')
os.environ.setdefault('DJANGO_DEBUG', '1')
os.environ.setdefault('DJANGO_ALLOWED_HOSTS', 'testserver,localhost')
os.environ.setdefault('OWN_ADMIN', '1')
os.environ.setdefault('DNS_DOMAIN', 'ddns.example.com')
os.environ.setdefault('DNS_HOST', 'ddns')
os.environ.setdefault('DNS_API_PORT', '8080')
os.environ.setdefault('DNS_SHARED_SECRET', 'test-shared-secret')
os.environ.setdefault('DNS_ALLOW_AGENT', 'ddclient,DynDNS')

import pytest
from django.contrib.auth import get_user_model


@pytest.fixture(autouse=True)
def _test_settings_overrides(settings):
    """Force a known-good config for every test.

    LANGUAGE_CODE 'en' matches what's in LANGUAGES (avoids i18n_patterns
    URL prefix mismatch). DNS_DOMAIN is set to a deterministic value so
    tests don't depend on the running container's .env.
    """
    settings.LANGUAGE_CODE = 'en'
    settings.DNS_DOMAIN = 'ddns.example.com'


@pytest.fixture
def admin_user(db):
    User = get_user_model()
    return User.objects.create_superuser(
        username='admin', email='admin@example.com', password='admin-pass'
    )


@pytest.fixture
def regular_user(db):
    User = get_user_model()
    return User.objects.create_user(
        username='bob', email='bob@example.com', password='bob-pass'
    )


@pytest.fixture
def other_user(db):
    User = get_user_model()
    return User.objects.create_user(
        username='alice', email='alice@example.com', password='alice-pass'
    )


@pytest.fixture
def admin_client(client, admin_user):
    client.force_login(admin_user)
    return client


@pytest.fixture
def user_client(client, regular_user):
    client.force_login(regular_user)
    return client
