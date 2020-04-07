# coding=utf-8

import requests

from guniflask.context import configuration, bean
from guniflask.oauth2_config import enable_resource_server, ResourceServerConfigurerAdapter
from guniflask.oauth2 import TokenStore, JwtTokenStore, JwtAccessTokenConverter
from guniflask.config import settings
from guniflask.security_config import enable_web_security, WebSecurityConfigurer, HttpSecurity


@configuration
@enable_resource_server
class MicroserviceResourceConfiguration(ResourceServerConfigurerAdapter):

    def __init__(self):
        self._jwt_access_token_converter = self._get_jwt_access_token_converter()

    @bean
    def token_store(self) -> TokenStore:
        return JwtTokenStore(self._jwt_access_token_converter)

    @bean
    def jwt_access_token_converter(self) -> JwtAccessTokenConverter:
        return self._jwt_access_token_converter

    def _get_jwt_access_token_converter(self):
        token_converter = JwtAccessTokenConverter()
        key_info = self._get_key_from_authorization_server()
        token_converter.signing_algorithm = key_info['alg']
        token_converter.verifying_key = key_info['value']
        return token_converter

    def _get_key_from_authorization_server(self):
        server: str = settings.get_by_prefix('guniflask.authorization_server')
        if not (server.startswith('http://') or server.startswith('https://')):
            server = 'http://' + server
        resp = requests.get('{}/oauth/token_key'.format(server.rstrip('/')))
        assert resp.status_code == 200, 'Failed to get token key from authorization server'
        return resp.json()


@configuration
@enable_web_security
class MicroserviceWebSecurityConfiguration(WebSecurityConfigurer):

    def configure_http(self, http: HttpSecurity):
        cors = settings.get_by_prefix('guniflask.cors')
        if cors:
            http.cors(cors)
