import os
import signal
import time

from guniflask_cli.gunicorn import GunicornApplication
from guniflask_cli.utils import pid_exists, read_pid
from .base import Command


class Stop(Command):
    @property
    def name(self):
        return 'stop'

    @property
    def short_desc(self):
        return 'Stop application'

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
            pid = read_pid(pidfile)
            if self.kill_pid(pid):
                not_found = False
                break
        if not_found:
            self.exitcode = 1
            print('No application to stop')

    def kill_pid(self, pid):
        if pid is None or not pid_exists(pid):
            return False
        print(f'kill {pid}')
        os.kill(pid, signal.SIGTERM)
        time.sleep(3)
        try:
            os.kill(pid, 0)
        except OSError:
            pass
        else:
            print('Application did not stop gracefully after 3 seconds')
            print(f'kill -9 {pid}')
            os.kill(pid, signal.SIGKILL)
        return True
