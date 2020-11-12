import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from guniflask.config import Settings

log = logging.getLogger(__name__)

db = SQLAlchemy()


def make_settings(app: Flask, settings: Settings):
    """
    This function is invoked before initializing app.
    """


def init_app(app: Flask, settings: Settings):
    """
    This function is invoked before running app.
    """
    _init_sqlalchemy(app, settings)


def _init_sqlalchemy(app, settings):
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
