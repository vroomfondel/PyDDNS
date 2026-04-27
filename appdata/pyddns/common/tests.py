import json
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from common.models import Activity_log


pytestmark = pytest.mark.django_db


# ---------- login (renders form) ----------

def test_login_page_renders(client):
    response = client.get(reverse('common:login'))
    assert response.status_code == 200


def test_login_url_resolvable():
    assert reverse('common:login').endswith('/login/')


# ---------- dologin (POST credentials) ----------

def _prime_test_cookie(client):
    """GET /common/login/ first so the test cookie is set in the session."""
    client.get(reverse('common:login'))


def test_dologin_success(client, regular_user):
    _prime_test_cookie(client)
    response = client.post(
        reverse('common:dologin'),
        {'username': 'bob', 'password': 'bob-pass'},
    )
    data = json.loads(response.content)
    assert data['success'] is True
    assert data['redirect'] == '/main/'


def test_dologin_wrong_password(client, regular_user):
    _prime_test_cookie(client)
    response = client.post(
        reverse('common:dologin'),
        {'username': 'bob', 'password': 'wrong'},
    )
    data = json.loads(response.content)
    assert data['success'] is False
    assert 'invalida' in data['errors']['reason'].lower()


def test_dologin_inactive_user(client, regular_user):
    regular_user.is_active = False
    regular_user.save()
    _prime_test_cookie(client)
    response = client.post(
        reverse('common:dologin'),
        {'username': 'bob', 'password': 'bob-pass'},
    )
    data = json.loads(response.content)
    assert data['success'] is False


def test_dologin_writes_activity_log(client, regular_user):
    _prime_test_cookie(client)
    client.post(
        reverse('common:dologin'),
        {'username': 'bob', 'password': 'bob-pass'},
    )
    assert Activity_log.objects.filter(action='DOLOGIN').exists()


def test_dologin_blocked_after_max_failures(client, regular_user):
    """After 5 failed DOLOGIN attempts in 10 min, requests get rejected."""
    _prime_test_cookie(client)
    for _ in range(5):
        Activity_log.objects.create(action='DOLOGIN', xforward='127.0.0.1', result='False - bad')
    response = client.post(
        reverse('common:dologin'),
        {'username': 'bob', 'password': 'bob-pass'},
    )
    data = json.loads(response.content)
    assert data['success'] is False
    assert 'maxima' in data['errors']['reason'].lower() or 'máxima' in data['errors']['reason'].lower()


# ---------- logout ----------

def test_logout_requires_login(client):
    response = client.get(reverse('common:logout'))
    assert response.status_code in (301, 302)
    assert 'login' in response['Location']


def test_logout_redirects_authenticated(user_client):
    response = user_client.get(reverse('common:logout'))
    assert response.status_code == 302
    assert '/common/login/' in response['Location']


# ---------- permission_denied / sin_permiso ----------

def test_permission_denied_renders(client):
    response = client.get(reverse('common:permission_denied'), follow=True)
    assert response.status_code == 200


# ---------- prune_activity_log management command ----------

def _make_log(action='SYNC', age_days=0):
    log = Activity_log.objects.create(action=action, code='good', result='ok')
    if age_days:
        Activity_log.objects.filter(pk=log.pk).update(
            date=timezone.now() - timedelta(days=age_days)
        )
    return log


def test_prune_deletes_only_old_rows():
    fresh = _make_log(age_days=1)
    old = _make_log(age_days=80)  # > 10 weeks (70 days)

    call_command('prune_activity_log', stdout=StringIO())

    assert Activity_log.objects.filter(pk=fresh.pk).exists()
    assert not Activity_log.objects.filter(pk=old.pk).exists()


def test_prune_respects_weeks_argument():
    in_window = _make_log(age_days=10)
    out_of_window = _make_log(age_days=20)

    call_command('prune_activity_log', '--weeks=2', stdout=StringIO())

    assert Activity_log.objects.filter(pk=in_window.pk).exists()
    assert not Activity_log.objects.filter(pk=out_of_window.pk).exists()


def test_prune_disabled_when_weeks_zero():
    log = _make_log(age_days=400)

    call_command('prune_activity_log', '--weeks=0', stdout=StringIO())

    assert Activity_log.objects.filter(pk=log.pk).exists()


def test_prune_dry_run_keeps_rows():
    log = _make_log(age_days=400)

    call_command('prune_activity_log', '--dry-run', stdout=StringIO())

    assert Activity_log.objects.filter(pk=log.pk).exists()
