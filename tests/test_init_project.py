# coding=utf-8

import os
from os.path import join, exists
import subprocess
import time
from threading import Thread
import json

from guniflask_cli import __version__


def show_version():
    res = subprocess.run("guniflask version", shell=True)
    assert res.returncode == 0


def init_project(proj_dir):
    settings = {
        'cli_version': __version__,
        'authentication_type': 'jwt',
        'port': 8000,
        'project_name': 'foo'
    }
    with open(join(proj_dir, '.guniflask-init.json'), 'w') as f:
        json.dump(settings, f)
    res = subprocess.run("cd '{}' && guniflask init".format(proj_dir),
                         shell=True)
    assert res.returncode == 0


def test_init_project(tmpdir, monkeypatch):
    proj_dir = join(str(tmpdir), 'foo')
    os.mkdir(proj_dir)
    show_version()
    init_project(proj_dir)
