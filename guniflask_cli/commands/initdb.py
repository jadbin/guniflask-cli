# coding=utf-8

import os

from guniflask_cli.utils import walk_modules
from guniflask_cli.errors import UsageError
from guniflask_cli.env import get_project_name_from_env
from guniflask_cli.config import load_app_settings
from .base import Command


class InitDb(Command):
    @property
    def name(self):
        return 'initdb'

    @property
    def syntax(self):
        return '[options]'

    @property
    def short_desc(self):
        return 'Initialize database from definition of models'

    def add_arguments(self, parser):
        parser.add_argument('-p', '--active-profiles', dest='active_profiles', metavar='PROFILES',
                            help='active profiles (comma-separated)')
        parser.add_argument('-f', '--force', dest='force', action='store_true', default=False,
                            help='force creating all tables')

    def process_arguments(self, args):
        if args.active_profiles:
            os.environ['GUNIFLASK_ACTIVE_PROFILES'] = args.active_profiles
        os.environ.setdefault('GUNIFLASK_ACTIVE_PROFILES', 'dev')

    def run(self, args):
        from guniflask.app import create_app

        project_name = get_project_name_from_env()
        settings = load_app_settings(project_name)

        walk_modules(project_name)
        app = create_app(project_name, settings=settings)
        with app.app_context():
            s = app.extensions.get('sqlalchemy')
            if not s:
                raise UsageError('Not found sqlalchemy')
            db = s.db
            if args.force:
                db.drop_all()
            else:
                print("\033[33mThe tables already exist will be skipped.\033[0m")
                print("\033[33mYou can try '-f' option to force creating all tables.\033[0m")
            db.create_all()
