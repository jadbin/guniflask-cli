import os
import signal
import time

import click

from guniflask_cli.gunicorn import GunicornApplication
from guniflask_cli.utils import pid_exists, read_pid


@click.group()
def cli_stop():
    pass


@cli_stop.command('stop')
@click.option('-p', '--active-profiles', metavar='PROFILES', help='Active profiles (comma-separated).')
def main(active_profiles):
    """
    Stop application.
    """
    Stop().run(active_profiles)


class Stop:
    def run(self, active_profiles):
        not_found = True
        if active_profiles:
            profile_list = [active_profiles]
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
