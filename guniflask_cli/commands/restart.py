# coding=utf-8

import os
import signal

from guniflask_cli.utils import pid_exists, read_pid
from guniflask_cli.gunicorn import GunicornApplication
from .base import Command


class Restart(Command):
    @property
    def name(self):
        return 'restart'

    @property
    def short_desc(self):
        return 'Restart application'

    def add_arguments(self, parser):
        parser.add_argument('-p', '--active-profiles', dest='active_profiles', metavar='PROFILES',
                            help='active profiles (comma-separated) which help to locate PID file')

    def run(self, args):
        not_found = True
        if args.active_profiles:
            profile_list = [args.active_profiles]
        else:
            profile_list = ['prod', 'dev']
        for p in profile_list:
            os.environ['GUNIFLASK_ACTIVE_PROFILES'] = p
            app = GunicornApplication()
            pidfile = app.options.get('pidfile')
            if pidfile:
                pid = read_pid(pidfile)
                if self.send_hup(pid):
                    not_found = False
                    break
        if not_found:
            print('No application to restart')
            self.exitcode = 1

    def send_hup(self, pid):
        if pid is None or not pid_exists(pid):
            return False
        print('Sending HUB signal to master (pid: {})'.format(pid))
        os.kill(pid, signal.SIGHUP)
        return True
