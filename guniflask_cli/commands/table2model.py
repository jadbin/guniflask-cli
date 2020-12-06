import os
from collections import defaultdict
from os.path import join

from flask import Flask
from sqlalchemy.schema import MetaData

from guniflask_cli.errors import UsageError
from guniflask_cli.sqlgen import SqlToModelGenerator
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
        parser.add_argument('--no-app', dest='no_app', action='store_true',
                            help='do conversion without initializing app')

    def process_arguments(self, args):
        if args.active_profiles:
            os.environ['GUNIFLASK_ACTIVE_PROFILES'] = args.active_profiles
        os.environ.setdefault('GUNIFLASK_ACTIVE_PROFILES', 'dev')

    def run(self, args):
        if args.no_app:
            from guniflask.app import AppInitializer
            from guniflask.config import load_app_env
            load_app_env()
            app_initializer = AppInitializer()
            app = Flask(app_initializer.name)
            app_initializer._make_settings(app)
            app_initializer._init_app(app)
        else:
            from guniflask.app import create_app
            app = create_app(with_context=False)
        app_name = app.name
        with app.app_context():
            settings = app.settings
            s = app.extensions.get('sqlalchemy')
            if not s:
                raise UsageError('Not found SQLAlchemy')
            db = s.db
            default_dest = defaultdict(dict)
            binds = [None] + list(app.config.get('SQLALCHEMY_BINDS') or ())
            for b in binds:
                if b is None:
                    default_dest[b] = {'dest': join(app_name, 'models')}
                else:
                    default_dest[b] = {'dest': join(app_name, f'models_{b}')}
            dest_config = settings.get_by_prefix('guniflask.table2model_dest', default_dest)
            if isinstance(dest_config, str):
                default_dest[None]['dest'] = dest_config
            else:
                for b in dest_config:
                    if b not in default_dest:
                        raise UsageError(f'"{b}" is not configured in binds')
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
                gen = SqlToModelGenerator(app_name, metadata, bind=b)
                gen.render(join(settings['home'], c.get('dest')))
