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

    def run(self, args):
        app = GunicornApplication()
        pid = read_pid(app.options.get('pidfile'))
        if pid is None or not pid_exists(pid):
            print('No application to stop')
            self.exitcode = 1
        else:
            print('Sending HUB signal to master (pid: {})'.format(pid))
            os.kill(pid, signal.SIGHUP)
