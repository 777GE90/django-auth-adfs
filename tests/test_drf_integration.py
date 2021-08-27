import json
from copy import deepcopy
from unittest.mock import patch

from django.test import RequestFactory, TestCase
from rest_framework import exceptions
from rest_framework.exceptions import AuthenticationFailed

from django_auth_adfs.config import ProviderConfig, Settings
from django_auth_adfs.rest_framework import AdfsAccessTokenAuthentication

from .utils import (
    build_access_token_adfs,
    build_access_token_azure,
    build_access_token_azure_guest,
    build_access_token_azure_not_guest,
    mock_adfs,
)


class RestFrameworkIntegrationTests(TestCase):
    def setUp(self):
        self.drf_auth_class = AdfsAccessTokenAuthentication()

        adfs_response = build_access_token_adfs(RequestFactory().get('/'))[2]
        self.access_token_adfs = json.loads(adfs_response)['access_token']

        azure_response = build_access_token_azure(RequestFactory().get('/'))[2]
        self.access_token_azure = json.loads(azure_response)['access_token']

        azure_response_guest = build_access_token_azure_guest(RequestFactory().get('/'))[2]
        self.access_token_azure_guest = json.loads(azure_response_guest)['access_token']

        azure_response_no_guest = build_access_token_azure_not_guest(RequestFactory().get('/'))[2]
        self.access_token_azure_no_guest = json.loads(azure_response_no_guest)['access_token']

    @mock_adfs('2012')
    def test_access_token_2012(self):
        access_token_header = f'Bearer {self.access_token_adfs}'
        request = RequestFactory().get('/api', HTTP_AUTHORIZATION=access_token_header)

        user, token = self.drf_auth_class.authenticate(request)
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(token, self.access_token_adfs.encode())

    @mock_adfs('2016')
    def test_access_token_2016(self):
        access_token_header = f'Bearer {self.access_token_adfs}'
        request = RequestFactory().get('/api', HTTP_AUTHORIZATION=access_token_header)

        user, token = self.drf_auth_class.authenticate(request)
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(token, self.access_token_adfs.encode())

    @mock_adfs('azure')
    def test_access_token_azure(self):
        access_token_header = f'Bearer {self.access_token_azure}'
        request = RequestFactory().get('/api', HTTP_AUTHORIZATION=access_token_header)

        from django_auth_adfs.config import django_settings

        settings = deepcopy(django_settings)
        del settings.AUTH_ADFS['SERVER']
        settings.AUTH_ADFS['TENANT_ID'] = 'dummy_tenant_id'
        with patch('django_auth_adfs.config.django_settings', settings):
            with patch('django_auth_adfs.config.settings', Settings()):
                with patch('django_auth_adfs.backend.provider_config', ProviderConfig()):
                    user, token = self.drf_auth_class.authenticate(request)
                    self.assertEqual(user.username, 'testuser')

    @mock_adfs('azure')
    def test_access_token_azure_guest(self):
        access_token_header = f'Bearer {self.access_token_azure_guest}'
        request = RequestFactory().get('/api', HTTP_AUTHORIZATION=access_token_header)

        from django_auth_adfs.config import django_settings

        settings = deepcopy(django_settings)
        del settings.AUTH_ADFS['SERVER']
        settings.AUTH_ADFS['TENANT_ID'] = 'dummy_tenant_id'
        settings.AUTH_ADFS['BLOCK_GUEST_USERS'] = True
        with patch('django_auth_adfs.config.django_settings', settings):
            with patch('django_auth_adfs.backend.settings', Settings()):
                with patch('django_auth_adfs.config.settings', Settings()):
                    with patch('django_auth_adfs.backend.provider_config', ProviderConfig()):
                        with self.assertRaises(AuthenticationFailed):
                            user, token = self.drf_auth_class.authenticate(request)

    @mock_adfs('azure')
    def test_access_token_azure_no_guest(self):
        access_token_header = f'Bearer {self.access_token_azure_no_guest}'
        request = RequestFactory().get('/api', HTTP_AUTHORIZATION=access_token_header)

        from django_auth_adfs.config import django_settings

        settings = deepcopy(django_settings)
        del settings.AUTH_ADFS['SERVER']
        settings.AUTH_ADFS['TENANT_ID'] = 'dummy_tenant_id'
        settings.AUTH_ADFS['BLOCK_GUEST_USERS'] = True
        with patch('django_auth_adfs.config.django_settings', settings):
            with patch('django_auth_adfs.backend.settings', Settings()):
                with patch('django_auth_adfs.config.settings', Settings()):
                    with patch('django_auth_adfs.backend.provider_config', ProviderConfig()):
                        user, token = self.drf_auth_class.authenticate(request)
                        self.assertEqual(user.username, 'testuser')

    @mock_adfs('2012')
    def test_access_token_exceptions(self):
        access_token_header = 'Bearer non-existing-token'
        request = RequestFactory().get('/api', HTTP_AUTHORIZATION=access_token_header)

        with self.assertRaises(exceptions.AuthenticationFailed):
            self.drf_auth_class.authenticate(request)

        # use the azure token on adfs should not work
        access_token_header = f'Bearer {self.access_token_azure}'
        request = RequestFactory().get('/api', HTTP_AUTHORIZATION=access_token_header)

        with self.assertRaises(exceptions.AuthenticationFailed):
            self.drf_auth_class.authenticate(request)
