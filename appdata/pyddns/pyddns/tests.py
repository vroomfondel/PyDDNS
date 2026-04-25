import base64
import json
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.urls import reverse
from django.utils import timezone

from common.models import Activity_log
from pyddns.models import Profile, SubDomain


pytestmark = pytest.mark.django_db


# =========================================================================
# Models
# =========================================================================

class TestSubDomainModel:
    def test_create(self, regular_user):
        sd = SubDomain.objects.create(name='myhost', user=regular_user)
        assert sd.pk is not None
        assert sd.user == regular_user

    def test_name_is_unique(self, regular_user):
        SubDomain.objects.create(name='dup', user=regular_user)
        with pytest.raises(IntegrityError):
            SubDomain.objects.create(name='dup', user=regular_user)


class TestProfileModel:
    def test_create_one_to_one(self, regular_user):
        Profile.objects.create(user=regular_user, city='Buenos Aires', description='admin')
        assert regular_user.profile.city == 'Buenos Aires'


class TestSettingsModule:
    def test_loaded(self):
        from django.conf import settings
        assert settings.SECRET_KEY
        assert 'pyddns' in settings.INSTALLED_APPS
        assert 'common' in settings.INSTALLED_APPS

    def test_production_requires_allowed_hosts(self, monkeypatch):
        import importlib
        import sys

        monkeypatch.setenv('DJANGO_SECRET_KEY', 'test')
        monkeypatch.setenv('DJANGO_ALLOWED_HOSTS', '')

        sys.modules.pop('pyddns.settings.production', None)
        sys.modules.pop('pyddns.settings.base', None)
        with pytest.raises(RuntimeError, match='DJANGO_ALLOWED_HOSTS'):
            importlib.import_module('pyddns.settings.production')


# =========================================================================
# main view (dashboard)
# =========================================================================

class TestMainView:
    def test_anonymous_redirected_to_login(self, client):
        response = client.get(reverse('main'))
        assert response.status_code in (301, 302)
        assert 'login' in response['Location']

    def test_authenticated_user_renders(self, user_client):
        response = user_client.get(reverse('main'))
        assert response.status_code == 200

    def test_admin_can_view_other_user_dashboard(self, admin_client, regular_user):
        response = admin_client.get(f'/main/{regular_user.id}', follow=True)
        assert response.status_code == 200


# =========================================================================
# users view (admin only)
# =========================================================================

class TestUsersView:
    def test_regular_user_denied(self, user_client):
        response = user_client.get(reverse('users'))
        assert response.status_code in (301, 302)
        assert 'permission_denied' in response['Location']

    def test_admin_allowed(self, admin_client, regular_user, other_user):
        response = admin_client.get(reverse('users'))
        assert response.status_code == 200

    def test_search_filter(self, admin_client, regular_user):
        response = admin_client.get(f'/users/{regular_user.username}', follow=True)
        assert response.status_code == 200


# =========================================================================
# domains view (admin only)
# =========================================================================

class TestDomainsView:
    def test_regular_user_denied(self, user_client):
        response = user_client.get(reverse('domains'))
        assert response.status_code in (301, 302)

    def test_admin_allowed(self, admin_client, regular_user):
        SubDomain.objects.create(name='test1', user=regular_user)
        response = admin_client.get(reverse('domains'))
        assert response.status_code == 200


# =========================================================================
# add_user view (admin only)
# =========================================================================

class TestAddUserView:
    def test_regular_user_denied(self, user_client):
        response = user_client.get(reverse('add_user'))
        assert response.status_code in (301, 302)

    def test_admin_renders_blank_form(self, admin_client):
        response = admin_client.get(reverse('add_user'))
        assert response.status_code == 200

    def test_admin_renders_with_existing_user(self, admin_client, regular_user):
        response = admin_client.get(f'/add_user/{regular_user.id}', follow=True)
        assert response.status_code == 200

    def test_admin_with_nonexistent_user_id(self, admin_client):
        response = admin_client.get('/add_user/999999', follow=True)
        assert response.status_code == 200


# =========================================================================
# add_subdomain view
# =========================================================================

class TestAddSubdomainView:
    def test_admin_creates_subdomain_for_self(self, admin_client, admin_user):
        response = admin_client.post(
            reverse('add_subdomain'),
            {'subdomain': 'newhost', 'id_user': admin_user.id},
        )
        data = json.loads(response.content)
        assert data['success'] is True
        assert SubDomain.objects.filter(name='newhost').exists()

    def test_admin_creates_subdomain_for_other_user(self, admin_client, regular_user):
        response = admin_client.post(
            reverse('add_subdomain'),
            {'subdomain': 'forothers', 'id_user': regular_user.id},
        )
        data = json.loads(response.content)
        assert data['success'] is True

    def test_user_creates_subdomain_for_self(self, user_client, regular_user):
        response = user_client.post(
            reverse('add_subdomain'),
            {'subdomain': 'mineonly', 'id_user': regular_user.id},
        )
        data = json.loads(response.content)
        assert data['success'] is True

    def test_user_cannot_create_for_other(self, user_client, regular_user, other_user):
        response = user_client.post(
            reverse('add_subdomain'),
            {'subdomain': 'stolen', 'id_user': other_user.id},
        )
        data = json.loads(response.content)
        assert data['success'] is False
        assert data['error'] == 'Not permission'

    def test_existing_subdomain_returns_exist(self, admin_client, admin_user):
        SubDomain.objects.create(name='taken', user=admin_user)
        response = admin_client.post(
            reverse('add_subdomain'),
            {'subdomain': 'taken', 'id_user': admin_user.id},
        )
        data = json.loads(response.content)
        assert data['error'] == 'exist'

    def test_anonymous_redirected(self, client, regular_user):
        response = client.post(
            reverse('add_subdomain'),
            {'subdomain': 'foo', 'id_user': regular_user.id},
        )
        assert response.status_code in (301, 302)

    @pytest.mark.parametrize('bad', [
        'has space', '<script>', 'a&b=c', 'evil.example.com',
        '-leadingdash', 'with_underscore', '',
    ])
    def test_invalid_subdomain_rejected(self, admin_client, admin_user, bad):
        response = admin_client.post(
            reverse('add_subdomain'),
            {'subdomain': bad, 'id_user': admin_user.id},
        )
        data = json.loads(response.content)
        assert data['error'] == 'invalid subdomain'
        assert data['success'] is False

    def test_invalid_user_id_rejected(self, admin_client):
        response = admin_client.post(
            reverse('add_subdomain'),
            {'subdomain': 'valid', 'id_user': 999999},
        )
        data = json.loads(response.content)
        assert data['error'] == 'invalid user'


# =========================================================================
# set_user view (admin only)
# =========================================================================

class TestSetUserView:
    def test_regular_user_denied(self, user_client):
        response = user_client.post(reverse('set_user'), {})
        assert response.status_code in (301, 302)

    def test_create_new_user(self, admin_client):
        response = admin_client.post(
            reverse('set_user'),
            {
                'username': 'newbie', 'name': 'New', 'last_name': 'Bie',
                'email': 'n@b.com', 'password': 'pwd', 'is_admin': '0',
            },
        )
        data = json.loads(response.content)
        assert data['success'] is True
        User = get_user_model()
        assert User.objects.filter(username='newbie').exists()

    def test_create_duplicate_username_fails(self, admin_client, regular_user):
        response = admin_client.post(
            reverse('set_user'),
            {
                'username': 'bob', 'name': 'Bob', 'last_name': 'X',
                'email': 'b@x.com', 'password': 'pwd', 'is_admin': '0',
            },
        )
        data = json.loads(response.content)
        assert 'exist' in data['error']

    def test_update_existing_user(self, admin_client, regular_user):
        response = admin_client.post(
            reverse('set_user'),
            {
                'id_user': regular_user.id, 'name': 'Bobby', 'last_name': 'Newname',
                'email': 'bob@new.com', 'password': '', 'is_admin': '1',
            },
        )
        data = json.loads(response.content)
        assert data['success'] is True
        regular_user.refresh_from_db()
        assert regular_user.first_name == 'Bobby'
        assert regular_user.is_superuser is True


# =========================================================================
# delet_user view (admin only)
# =========================================================================

class TestDeletUserView:
    def test_regular_user_denied(self, user_client):
        response = user_client.post(reverse('del_user'), {})
        assert response.status_code in (301, 302)

    def test_admin_deletes(self, admin_client, regular_user):
        user_id = regular_user.id
        response = admin_client.post(reverse('del_user'), {'id_user': user_id})
        data = json.loads(response.content)
        assert data['success'] is True
        User = get_user_model()
        assert not User.objects.filter(id=user_id).exists()


# =========================================================================
# delet_domain view
# =========================================================================

class TestDeletDomainView:
    def test_anonymous_redirected(self, client):
        response = client.post(reverse('delete_domain'), {})
        assert response.status_code in (301, 302)

    def test_owner_can_delete(self, user_client, regular_user):
        sd = SubDomain.objects.create(name='mine', user=regular_user)
        response = user_client.post(reverse('delete_domain'), {'id_domain': sd.id})
        data = json.loads(response.content)
        assert data['success'] is True
        assert not SubDomain.objects.filter(id=sd.id).exists()

    def test_admin_can_delete_any(self, admin_client, regular_user):
        sd = SubDomain.objects.create(name='someone-elses', user=regular_user)
        response = admin_client.post(reverse('delete_domain'), {'id_domain': sd.id})
        data = json.loads(response.content)
        assert data['success'] is True

    def test_non_owner_cannot_delete(self, user_client, other_user):
        sd = SubDomain.objects.create(name='alices', user=other_user)
        response = user_client.post(reverse('delete_domain'), {'id_domain': sd.id})
        data = json.loads(response.content)
        assert data['success'] is False
        assert data['error'] == 'permission'


# =========================================================================
# set_ip / set_ip_web (DNS update with mocks)
# =========================================================================

def _mock_resolver(returned_ip):
    """Build a dns.resolver.Resolver mock whose .resolve() returns returned_ip."""
    fake = MagicMock()
    instance = fake.return_value
    instance.resolve.return_value = [returned_ip]
    return fake


class TestSetIpWebView:
    @patch('pyddns.views.requests.get')
    @patch('pyddns.views.socket.gethostbyname', return_value='10.0.0.1')
    @patch('pyddns.views.dns.resolver.Resolver', new_callable=lambda: _mock_resolver('1.1.1.1'))
    def test_owner_updates_ip_successfully(self, mock_resolver, mock_socket, mock_get,
                                           user_client, regular_user):
        SubDomain.objects.create(name='myhost', user=regular_user)
        mock_get.return_value.json.return_value = {'Success': True}

        response = user_client.get('/en/ip/update/myhost.ddns.example.com/2.2.2.2')
        data = json.loads(response.content)
        assert data['success'] is True
        mock_get.assert_called_once()

    @patch('pyddns.views.requests.get')
    @patch('pyddns.views.socket.gethostbyname', return_value='10.0.0.1')
    @patch('pyddns.views.dns.resolver.Resolver', new_callable=lambda: _mock_resolver('2.2.2.2'))
    def test_no_change_when_ip_already_matches(self, mock_resolver, mock_socket, mock_get,
                                               user_client, regular_user):
        SubDomain.objects.create(name='myhost', user=regular_user)

        response = user_client.get('/en/ip/update/myhost.ddns.example.com/2.2.2.2')
        data = json.loads(response.content)
        assert data['success'] is False  # nochg sets only message, not success
        mock_get.assert_not_called()

    def test_anonymous_redirected_to_login(self, client):
        response = client.get('/en/ip/update/whatever.ddns.example.com/1.2.3.4')
        assert response.status_code in (301, 302)
        assert 'login' in response['Location']

    def test_invalid_ip_rejected(self, user_client, regular_user):
        SubDomain.objects.create(name='myhost', user=regular_user)
        response = user_client.get('/en/ip/update/myhost.ddns.example.com/not-an-ip')
        data = json.loads(response.content)
        assert data['success'] is False
        assert 'invalid ip' in data['message']

    def test_unknown_subdomain_does_not_500(self, user_client):
        response = user_client.get('/en/ip/update/nonexistent.ddns.example.com/1.2.3.4')
        data = json.loads(response.content)
        assert data['success'] is False
        assert 'unknown subdomain' in data['message']


# =========================================================================
# updateip view (dyndns2 protocol /nic/update)
# =========================================================================

def _basic_auth_header(username, password):
    creds = base64.b64encode(f'{username}:{password}'.encode()).decode()
    return f'Basic {creds}'


class TestUpdateIpView:
    URL = '/nic/update'

    def test_no_user_agent_returns_badagent(self, client):
        response = client.get(self.URL, HTTP_USER_AGENT='curl/8.0')
        assert response.content.decode() == 'badagent'

    def test_unknown_when_no_auth_header(self, client):
        response = client.get(self.URL, HTTP_USER_AGENT='ddclient/3.9')
        assert response.content.decode() == 'unknown'

    def test_badauth_when_credentials_invalid(self, client):
        response = client.get(
            self.URL,
            HTTP_USER_AGENT='ddclient/3.9',
            HTTP_AUTHORIZATION=_basic_auth_header('nope', 'nope'),
        )
        assert response.content.decode() == 'badauth'

    def test_nohost_when_subdomain_not_owned(self, client, regular_user):
        response = client.get(
            self.URL + '?hostname=other.ddns.example.com&myip=1.2.3.4',
            HTTP_USER_AGENT='ddclient/3.9',
            HTTP_AUTHORIZATION=_basic_auth_header('bob', 'bob-pass'),
        )
        assert response.content.decode() == 'nohost'

    @patch('pyddns.views.requests.get')
    @patch('pyddns.views.socket.gethostbyname', return_value='10.0.0.1')
    @patch('pyddns.views.dns.resolver.Resolver', new_callable=lambda: _mock_resolver('1.1.1.1'))
    def test_good_when_valid_owner_and_dns_changed(self, mock_resolver, mock_socket, mock_get,
                                                   client, regular_user):
        SubDomain.objects.create(name='myhost', user=regular_user)
        mock_get.return_value.json.return_value = {'Success': True}

        response = client.get(
            self.URL + '?hostname=myhost.ddns.example.com&myip=2.2.2.2',
            HTTP_USER_AGENT='ddclient/3.9',
            HTTP_AUTHORIZATION=_basic_auth_header('bob', 'bob-pass'),
        )
        assert response.content.decode() == 'good'

    @patch('pyddns.views.requests.get')
    @patch('pyddns.views.socket.gethostbyname', return_value='10.0.0.1')
    @patch('pyddns.views.dns.resolver.Resolver', new_callable=lambda: _mock_resolver('1.1.1.1'))
    def test_dnserr_when_bind_call_fails(self, mock_resolver, mock_socket, mock_get,
                                         client, regular_user):
        SubDomain.objects.create(name='myhost', user=regular_user)
        mock_get.return_value.json.return_value = {'Success': False}

        response = client.get(
            self.URL + '?hostname=myhost.ddns.example.com&myip=2.2.2.2',
            HTTP_USER_AGENT='ddclient/3.9',
            HTTP_AUTHORIZATION=_basic_auth_header('bob', 'bob-pass'),
        )
        assert response.content.decode() == 'dnserr'

    def test_abuse_after_many_failures(self, client, regular_user):
        for _ in range(10):
            Activity_log.objects.create(
                action='SYNC', ip='1.2.3.4', date=timezone.now(), result='False - bad',
            )
        response = client.get(
            self.URL + '?hostname=myhost.ddns.example.com&myip=1.2.3.4',
            HTTP_USER_AGENT='ddclient/3.9',
            HTTP_AUTHORIZATION=_basic_auth_header('bob', 'bob-pass'),
        )
        assert response.content.decode() == 'abuse'
