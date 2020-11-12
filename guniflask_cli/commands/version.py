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
        print(f"  guniflask-cli: v{__version__}")
        try:
            import guniflask
        except ImportError:
            pass
        else:
            print(f"  guniflask: v{guniflask.__version__}")
