import os

import click

from guniflask_cli.gunicorn import GunicornApplication


@click.group()
def cli_debug():
    pass


@cli_debug.command('debug')
@click.option('-d', '--daemon', default=False, is_flag=True, help='Run in daemon mode.')
@click.option('-p', '--active-profiles', metavar='PROFILES', help='Active profiles (comma-separated).')
def main(daemon, active_profiles):
    """
    Debug application.
    """
    Debug().run(daemon, active_profiles)


class Debug:
    def run(self, daemon, active_profiles):
        if active_profiles:
            os.environ['GUNIFLASK_ACTIVE_PROFILES'] = active_profiles
        os.environ['GUNIFLASK_DEBUG'] = '1'
        os.environ.setdefault('GUNIFLASK_ACTIVE_PROFILES', 'dev')

        opt = {}
        if daemon:
            opt['daemon'] = True
        app = GunicornApplication(**opt)
        app.run()
