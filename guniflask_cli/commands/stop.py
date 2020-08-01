# coding=utf-8

import os
import signal
import time

from guniflask_cli.utils import pid_exists, read_pid
from guniflask_cli.gunicorn import GunicornApplication
from .base import Command


class Stop(Command):
    @property
    def name(self):
        return 'stop'

    @property
    def short_desc(self):
        return 'Stop application'

    def run(self, args):
        app = GunicornApplication()
        pid = read_pid(app.options.get('pidfile'))
        if pid is None or not pid_exists(pid):
            print('No application to stop')
            self.exitcode = 1
        else:
            print('kill {}'.format(pid))
            os.kill(pid, signal.SIGTERM)
            time.sleep(3)
            try:
                os.kill(pid, 0)
            except OSError:
                pass
            else:
                print('Application did not stop gracefully after 3 seconds')
                print('kill -9 {}'.format(pid))
                os.kill(pid, signal.SIGKILL)
