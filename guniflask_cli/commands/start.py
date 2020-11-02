# coding=utf-8

import os

from guniflask_cli.gunicorn import GunicornApplication
from .base import Command


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
        opt = {}
        if args.daemon_off:
            opt['daemon'] = False
        app = GunicornApplication(**opt)

        app.run()
