# coding=utf-8

from guniflask_cli import __version__
from .base import Command


class VersionCommand(Command):
    @property
    def name(self):
        return "version"

    @property
    def short_desc(self):
        return "Print the version"

    def run(self, args):
        print("  guniflask-cli: v{}".format(__version__))
        try:
            import guniflask
        except ImportError:
            pass
        else:
            print("  guniflask: v{}".format(guniflask.__version__))
