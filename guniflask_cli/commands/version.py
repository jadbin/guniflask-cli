import click

from guniflask_cli import __version__


@click.group()
def cli_version():
    pass


@cli_version.command('version')
def main():
    """
    Print the version.
    """
    Version().run()


class Version:
    def run(self):
        print(f"  guniflask-cli: v{__version__}")

        import guniflask
        print(f"  guniflask: v{guniflask.__version__}")
