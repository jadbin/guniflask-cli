import os
import signal

import click

from guniflask_cli.gunicorn import GunicornApplication
from guniflask_cli.utils import pid_exists, read_pid


@click.group()
def cli_restart():
    pass


@cli_restart.command('restart')
@click.option('-p', '--active-profiles', metavar='PROFILES', help='Active profiles (comma-separated).')
def main(active_profiles):
    """
    Restart application.
    """
    Restart().run(active_profiles)


class Restart:
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
        print(f'Sending HUB signal to master (pid: {pid})')
        os.kill(pid, signal.SIGHUP)
        return True
