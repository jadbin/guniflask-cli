# coding=utf-8

import logging

from flask_sqlalchemy import SQLAlchemy

log = logging.getLogger(__name__)

db = SQLAlchemy()


def make_settings(app, settings):
    """
    This function is invoked before initializing app.
    """


def init_app(app, settings):
    """
    This function is invoked before running app.
    """
    _init_sqlalchemy(app, settings)


def _init_sqlalchemy(app, settings):
    db.init_app(app)
    do_wrap = settings.get_by_prefix('guniflask.wrap_sqlalchemy_model', True)
    if do_wrap:
        from guniflask.orm import wrap_sqlalchemy_model
        wrap_sqlalchemy_model(db.Model)
