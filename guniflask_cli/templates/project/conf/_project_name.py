# coding=utf-8

# Database URI, example: mysql://username:password@server/db?charset=utf8mb4
# SQLALCHEMY_DATABASE_URI = ''


# guniflask configuration
guniflask = dict({% if application_type == 'microservice' and authentication_type == 'authorization_server' %}
    authorization_server='authorization server address',{% endif %}{% if authentication_type == 'jwt' %}
    jwt=dict(
        secret='{{jwt_secret}}'
    ),{% endif %}
)
