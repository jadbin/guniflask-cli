# coding=utf-8

import sys
import argparse
import inspect

from .commands.base import Command
from .errors import UsageError
from .utils import walk_modules
from .env import set_default_env


def _get_commands_from_module():
    d = {}
    for m in walk_modules('guniflask_cli.commands'):
        for cmd in vars(m).values():
            if inspect.isclass(cmd) and issubclass(cmd, Command):
                o = cmd()
                if o.name:
                    d[o.name] = o
    return d


def _print_commands():
    print("Usage: guniflask <command> [options] [args]\n")
    print("Available commands:")
    cmds = _get_commands_from_module()
    for cmdname, cmdclass in sorted(cmds.items()):
        print("  {:<14} {}".format(cmdname, cmdclass.short_desc))
    print()
    print('Use "guniflask <command> -h" to see more info about a command')


def _print_unknown_command(cmdname):
    print("Unknown command: %s\n" % cmdname)
    print('Use "guniflask" to see available commands')


def main(argv=None):
    set_default_env()
    if argv is None:
        argv = sys.argv
    cmds = _get_commands_from_module()
    cmdname = argv[1] if len(argv) > 1 else None
    if not cmdname:
        _print_commands()
        sys.exit(0)
    elif cmdname not in cmds:
        _print_unknown_command(cmdname)
        sys.exit(2)
    del argv[1]
    cmd = cmds[cmdname]
    parser = argparse.ArgumentParser()
    parser.usage = "guniflask {} {}".format(cmdname, cmd.syntax)
    parser.description = cmd.long_desc
    cmd.add_arguments(parser)
    try:
        args = parser.parse_args(args=argv[1:])
        cmd.process_arguments(args)
        cmd.run(args)
    except UsageError as e:
        if e.print_help:
            parser.print_help(sys.stderr)
        print('Error: {}'.format(e), file=sys.stderr)
        sys.exit(2)
    else:
        if cmd.exitcode:
            sys.exit(cmd.exitcode)
