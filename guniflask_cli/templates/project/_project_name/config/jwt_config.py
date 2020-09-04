# coding=utf-8

from guniflask.security_config.security_configurer import SecurityConfigurer
from guniflask.security_config.http_security import HttpSecurityBuilder
from guniflask.security.jwt_provider import JwtManager
from guniflask.security.context import SecurityContext
from guniflask.web import RequestFilter
from guniflask.oauth2 import BearerTokenExtractor


class JwtConfigurer(SecurityConfigurer):
    def __init__(self, jwt=None):
        super().__init__()
        self.jwt_filter = None
        if isinstance(jwt, dict):
            jwt_manager = JwtManager(**jwt)
            self.jwt_filter = JwtFilter(jwt_manager)

    def configure(self, http: HttpSecurityBuilder):
        if self.jwt_filter:
            http.add_request_filter(self.jwt_filter)


class JwtFilter(RequestFilter):
    def __init__(self, jwt_manager: JwtManager):
        self.jwt_manager = jwt_manager
        self.token_extractor = BearerTokenExtractor()

    def before_request(self):
        auth = self.token_extractor.extract()
        if auth is not None:
            user_auth = self.jwt_manager.authenticate(auth)
            SecurityContext.set_authentication(user_auth)
