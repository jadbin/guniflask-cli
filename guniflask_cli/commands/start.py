# coding=utf-8

import os

from guniflask_cli.gunicorn import GunicornApplication
from .base import Command, check_pid


class Start(Command):
    @property
    def name(self):
        return 'start'

    @property
    def short_desc(self):
        return 'Start application'

    def add_arguments(self, parser):
        parser.add_argument('--daemon-off', dest='daemon_off', action='store_true', help='turn off daemon mode')
        parser.add_argument('-p', '--active-profiles', dest='active_profiles', metavar='PROFILES',
                            help='active profiles (comma-separated)')

    def process_arguments(self, args):
        if args.active_profiles:
            os.environ['GUNIFLASK_ACTIVE_PROFILES'] = args.active_profiles
        os.environ.setdefault('GUNIFLASK_ACTIVE_PROFILES', 'prod')

    def run(self, args):
        app = GunicornApplication()
        if args.daemon_off:
            app.set_option('daemon', False)

        pidfile = app.options.get('pidfile')
        if pidfile and not check_pid(pidfile):
            self.exitcode = 1
        else:
            app.run()
