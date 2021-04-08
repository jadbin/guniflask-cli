import click

from .commands.build import cli_build
from .commands.debug import cli_debug
from .commands.init import cli_init
from .commands.restart import cli_restart
from .commands.start import cli_start
from .commands.stop import cli_stop
from .commands.table2model import cli_table2model
from .commands.version import cli_version

main = click.CommandCollection(
    sources=[
        cli_build,
        cli_debug,
        cli_init,
        cli_restart,
        cli_start,
        cli_stop,
        cli_table2model,
        cli_version,
    ]
)
