# coding=utf-8

import os
from os.path import join
from collections import defaultdict

from sqlalchemy.schema import MetaData

from guniflask_cli.sqlgen import SqlToModelGenerator
from guniflask_cli.errors import UsageError
from guniflask_cli.env import get_project_name_from_env
from guniflask_cli.config import load_app_settings
from .base import Command


class TableToModel(Command):
    @property
    def name(self):
        return 'table2model'

    @property
    def syntax(self):
        return '[options]'

    @property
    def short_desc(self):
        return 'Convert database tables to definition of models'

    def add_arguments(self, parser):
        parser.add_argument('-p', '--active-profiles', dest='active_profiles', metavar='PROFILES',
                            help='active profiles (comma-separated)')

    def process_arguments(self, args):
        if args.active_profiles:
            os.environ['GUNIFLASK_ACTIVE_PROFILES'] = args.active_profiles
        os.environ.setdefault('GUNIFLASK_ACTIVE_PROFILES', 'dev')

    def run(self, args):
        from guniflask.app import create_app

        project_name = get_project_name_from_env()
        settings = load_app_settings(project_name)

        app = create_app(project_name, settings=settings)
        with app.app_context():
            settings = app.extensions['settings']
            s = app.extensions.get('sqlalchemy')
            if not s:
                raise UsageError('Not found SQLAlchemy')
            db = s.db
            default_dest = defaultdict(dict)
            binds = [None] + list(app.config.get('SQLALCHEMY_BINDS') or ())
            for b in binds:
                if b is None:
                    default_dest[b] = {'dest': join(project_name, 'models')}
                else:
                    default_dest[b] = {'dest': join(project_name, 'models_{}'.format(b))}
            dest_config = settings.get_by_prefix('guniflask.table2model_dest', default_dest)
            if isinstance(default_dest, str):
                default_dest[None]['dest'] = dest_config
            else:
                for b in dest_config:
                    if b not in default_dest:
                        raise UsageError('"{}" is not configured in binds'.format(b))
                    c = dest_config[b]
                    if isinstance(c, str):
                        default_dest[b]['dest'] = c
                    else:
                        default_dest[b].update(c)
            for b in default_dest:
                c = default_dest[b]
                engine = db.get_engine(bind=b)
                metadata = MetaData(engine)
                metadata.reflect()
                gen = SqlToModelGenerator(project_name, metadata, bind=b)
                gen.render(join(settings['home'], c.get('dest')))
