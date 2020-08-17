# coding=utf-8

from guniflask_cli.utils import read_pid, pid_exists


class Command:
    def __init__(self):
        self.exitcode = 0

    @property
    def name(self):
        return ""

    @property
    def syntax(self):
        return ""

    @property
    def short_desc(self):
        return ""

    @property
    def long_desc(self):
        return self.short_desc

    def add_arguments(self, parser):
        pass

    def process_arguments(self, args):
        pass

    def run(self, args):
        raise NotImplementedError


def check_pid(pidfile):
    pid = read_pid(pidfile)
    if pid is not None and pid_exists(pid):
        print('Application is already started')
        return False
    return True
