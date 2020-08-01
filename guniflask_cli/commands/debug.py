# coding=utf-8

import os

from guniflask_cli.utils import pid_exists, read_pid
from guniflask_cli.gunicorn import GunicornApplication
from .base import Command


class Debug(Command):
    @property
    def name(self):
        return 'debug'

    @property
    def short_desc(self):
        return 'Debug application'

    def add_arguments(self, parser):
        parser.add_argument('-d', '--daemon', dest='daemon', action='store_true', help='run in daemon mode')
        parser.add_argument('-p', '--active-profiles', dest='active_profiles', metavar='PROFILES',
                            help='active profiles (comma-separated)')

    def process_arguments(self, args):
        if args.active_profiles:
            os.environ['GUNIFLASK_ACTIVE_PROFILES'] = args.active_profiles
        os.environ['GUNIFLASK_DEBUG'] = '1'
        os.environ.setdefault('GUNIFLASK_ACTIVE_PROFILES', 'dev')

    def run(self, args):
        app = GunicornApplication()
        if args.daemon:
            app.set_option('daemon', True)
        pid = read_pid(app.options.get('pidfile'))
        if pid is not None and pid_exists(pid):
            print('Application is already started')
            self.exitcode = 1
        else:
            app.run()
