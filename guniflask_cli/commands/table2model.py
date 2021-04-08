import os
from collections import defaultdict
from os.path import join

import click
from flask import Flask
from sqlalchemy.schema import MetaData

from guniflask_cli.errors import UsageError
from guniflask_cli.sqlgen import SqlToModelGenerator


@click.group()
def cli_table2model():
    pass


@cli_table2model.command('table2model')
@click.option('-p', '--active-profiles', metavar='PROFILES', help='Active profiles (comma-separated).')
@click.option('--no-app', default=False, is_flag=True, help='Do conversion without initializing app.')
def main(active_profiles, no_app):
    """
    Convert database tables to definition of models.
    """
    TableToModel().run(active_profiles, no_app)


class TableToModel:
    def run(self, active_profiles, no_app):
        if active_profiles:
            os.environ['GUNIFLASK_ACTIVE_PROFILES'] = active_profiles
        os.environ.setdefault('GUNIFLASK_ACTIVE_PROFILES', 'dev')

        if no_app:
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
