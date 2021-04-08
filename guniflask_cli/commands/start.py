import os

import click

from guniflask_cli.gunicorn import GunicornApplication


@click.group()
def cli_start():
    pass


@cli_start.command('start')
@click.option('--daemon-off', default=False, is_flag=True, help='Turn off daemon mode.')
@click.option('-p', '--active-profiles', metavar='PROFILES', help='Active profiles (comma-separated).')
def main(daemon_off, active_profiles):
    """
    Start application.
    """
    Start().run(daemon_off, active_profiles)


class Start:
    def run(self, daemon_off, active_profiles):
        if active_profiles:
            os.environ['GUNIFLASK_ACTIVE_PROFILES'] = active_profiles
        os.environ.setdefault('GUNIFLASK_ACTIVE_PROFILES', 'prod')

        opt = {}
        if daemon_off:
            opt['daemon'] = False
        app = GunicornApplication(**opt)

        app.run()
