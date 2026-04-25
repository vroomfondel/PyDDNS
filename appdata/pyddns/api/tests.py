from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from common.models import Activity_log
from pyddns.models import SubDomain


pytestmark = pytest.mark.django_db


# ---------- fixtures ----------

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_token(regular_user):
    return Token.objects.create(user=regular_user)


@pytest.fixture
def admin_token(admin_user):
    return Token.objects.create(user=admin_user)


@pytest.fixture
def auth_user_client(api_client, user_token):
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {user_token.key}')
    return api_client


@pytest.fixture
def auth_admin_client(api_client, admin_token):
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {admin_token.key}')
    return api_client


# ---------- /api/auth/token/ ----------

class TestTokenEndpoints:
    def test_obtain_token_with_valid_credentials(self, api_client, regular_user):
        response = api_client.post(
            '/api/auth/token/',
            {'username': 'bob', 'password': 'bob-pass'},
        )
        assert response.status_code == 200
        assert 'token' in response.data

    def test_obtain_token_rejects_invalid_credentials(self, api_client, regular_user):
        response = api_client.post(
            '/api/auth/token/',
            {'username': 'bob', 'password': 'wrong'},
        )
        assert response.status_code == 400

    def test_revoke_token(self, auth_user_client, user_token):
        response = auth_user_client.post('/api/auth/token/revoke/')
        assert response.status_code == 204
        assert not Token.objects.filter(key=user_token.key).exists()

    def test_revoke_requires_auth(self, api_client):
        response = api_client.post('/api/auth/token/revoke/')
        assert response.status_code == 401


# ---------- /api/me/ ----------

class TestMeEndpoint:
    def test_returns_user_info(self, auth_user_client, regular_user):
        response = auth_user_client.get('/api/me/')
        assert response.status_code == 200
        assert response.data['username'] == 'bob'
        assert response.data['is_superuser'] is False

    def test_anonymous_unauthorized(self, api_client):
        response = api_client.get('/api/me/')
        assert response.status_code == 401


# ---------- /api/subdomains/ ----------

class TestSubdomainViewSet:
    def test_list_returns_only_own(self, auth_user_client, regular_user, other_user):
        SubDomain.objects.create(name='mine', user=regular_user)
        SubDomain.objects.create(name='theirs', user=other_user)

        response = auth_user_client.get('/api/subdomains/')
        names = [s['name'] for s in response.data['results']]
        assert names == ['mine']

    def test_admin_sees_all(self, auth_admin_client, regular_user, admin_user):
        SubDomain.objects.create(name='userone', user=regular_user)
        SubDomain.objects.create(name='admone', user=admin_user)

        response = auth_admin_client.get('/api/subdomains/')
        assert response.data['count'] == 2

    def test_create_assigns_to_caller(self, auth_user_client, regular_user):
        response = auth_user_client.post('/api/subdomains/', {'name': 'newone'})
        assert response.status_code == 201
        sd = SubDomain.objects.get(name='newone')
        assert sd.user == regular_user

    def test_create_validates_name(self, auth_user_client):
        response = auth_user_client.post('/api/subdomains/', {'name': 'invalid name'})
        assert response.status_code == 400
        assert 'name' in response.data

    def test_user_cannot_delete_others_subdomain(self, auth_user_client, other_user):
        sd = SubDomain.objects.create(name='alices', user=other_user)
        response = auth_user_client.delete(f'/api/subdomains/{sd.id}/')
        assert response.status_code == 404  # filtered out of queryset

    def test_owner_can_delete_own(self, auth_user_client, regular_user):
        sd = SubDomain.objects.create(name='mine2', user=regular_user)
        response = auth_user_client.delete(f'/api/subdomains/{sd.id}/')
        assert response.status_code == 204
        assert not SubDomain.objects.filter(id=sd.id).exists()

    def test_admin_can_delete_anyones(self, auth_admin_client, other_user):
        sd = SubDomain.objects.create(name='target', user=other_user)
        response = auth_admin_client.delete(f'/api/subdomains/{sd.id}/')
        assert response.status_code == 204

    def test_anonymous_unauthorized(self, api_client):
        response = api_client.get('/api/subdomains/')
        assert response.status_code == 401


# ---------- /api/subdomains/<id>/update_ip/ ----------

def _resolver_returning(ip_str):
    fake = MagicMock()
    fake.return_value.resolve.return_value = [ip_str]
    return fake


class TestUpdateIpAction:
    @patch('pyddns.views.requests.get')
    @patch('pyddns.views.socket.gethostbyname', return_value='10.0.0.1')
    @patch('pyddns.views.dns.resolver.Resolver',
           new_callable=lambda: _resolver_returning('1.1.1.1'))
    def test_update_calls_bind(self, mock_resolver, mock_socket, mock_get,
                               auth_user_client, regular_user):
        sd = SubDomain.objects.create(name='myhost', user=regular_user)
        mock_get.return_value.json.return_value = {'Success': True}

        response = auth_user_client.post(
            f'/api/subdomains/{sd.id}/update_ip/',
            {'ip': '2.2.2.2'},
        )
        assert response.status_code == 200
        assert response.data['code'] == 'good'
        mock_get.assert_called_once()

    def test_invalid_ip_rejected(self, auth_user_client, regular_user):
        sd = SubDomain.objects.create(name='myhost', user=regular_user)
        response = auth_user_client.post(
            f'/api/subdomains/{sd.id}/update_ip/',
            {'ip': 'not-an-ip'},
        )
        assert response.status_code == 400

    def test_writes_activity_log(self, auth_user_client, regular_user):
        sd = SubDomain.objects.create(name='myhost', user=regular_user)
        with patch('pyddns.views.dns.resolver.Resolver',
                   new_callable=lambda: _resolver_returning('5.5.5.5')), \
             patch('pyddns.views.socket.gethostbyname', return_value='10.0.0.1'), \
             patch('pyddns.views.requests.get') as mock_get:
            mock_get.return_value.json.return_value = {'Success': True}
            auth_user_client.post(
                f'/api/subdomains/{sd.id}/update_ip/',
                {'ip': '6.6.6.6'},
            )
        assert Activity_log.objects.filter(
            action='SYNC',
            user_affected='bob',
            code='good',
        ).exists()


# ---------- /api/users/ (admin only) ----------

class TestUserViewSet:
    def test_regular_user_forbidden(self, auth_user_client):
        response = auth_user_client.get('/api/users/')
        assert response.status_code == 403

    def test_admin_lists_all(self, auth_admin_client, admin_user, regular_user):
        response = auth_admin_client.get('/api/users/')
        assert response.data['count'] >= 2

    def test_admin_creates_user(self, auth_admin_client):
        response = auth_admin_client.post(
            '/api/users/',
            {
                'username': 'newone',
                'email': 'new@example.com',
                'password': 'a-strong-password-123',
            },
        )
        assert response.status_code == 201
        from django.contrib.auth import get_user_model
        User = get_user_model()
        new_user = User.objects.get(username='newone')
        assert new_user.check_password('a-strong-password-123')


# ---------- /api/activity/ ----------

class TestActivityLog:
    def test_user_sees_only_own_entries(self, auth_user_client, regular_user, other_user):
        Activity_log.objects.create(action='SYNC', user_affected='bob', result='ok')
        Activity_log.objects.create(action='SYNC', user_affected='alice', result='ok')

        response = auth_user_client.get('/api/activity/')
        names = {e['user_affected'] for e in response.data['results']}
        assert names == {'bob'}

    def test_admin_sees_all(self, auth_admin_client):
        Activity_log.objects.create(action='SYNC', user_affected='bob', result='ok')
        Activity_log.objects.create(action='SYNC', user_affected='alice', result='ok')

        response = auth_admin_client.get('/api/activity/')
        assert response.data['count'] >= 2

    def test_is_read_only(self, auth_admin_client):
        response = auth_admin_client.post('/api/activity/', {'action': 'X'})
        assert response.status_code == 405  # POST not allowed


class TestApiToggleable:
    """The REST API is gated by the ENABLE_REST_API setting."""

    def test_setting_is_active_during_tests(self):
        from django.conf import settings
        assert settings.ENABLE_REST_API is True
        assert 'rest_framework' in settings.INSTALLED_APPS
        assert 'api' in settings.INSTALLED_APPS
