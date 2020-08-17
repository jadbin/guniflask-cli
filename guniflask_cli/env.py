# coding=utf-8

import os
import sys
from os.path import join, isfile, isdir
import re
import json

__all__ = ['set_default_env', 'infer_project_name', 'get_project_name_from_env']


def set_default_env():
    home_dir = os.environ.get('GUNIFLASK_HOME')
    if not home_dir:
        home_dir = os.getcwd()
        os.environ['GUNIFLASK_HOME'] = home_dir
    if home_dir not in sys.path:
        sys.path.append(home_dir)
    if not os.environ.get('GUNIFLASK_PROJECT_NAME'):
        project_name = infer_project_name(home_dir)
        if project_name:
            os.environ['GUNIFLASK_PROJECT_NAME'] = project_name
    if not os.environ.get('GUNIFLASK_CONF_DIR'):
        os.environ['GUNIFLASK_CONF_DIR'] = join(home_dir, 'conf')
    if not os.environ.get('GUNIFLASK_LOG_DIR'):
        os.environ['GUNIFLASK_LOG_DIR'] = join(home_dir, '.log')
    if not os.environ.get('GUNIFLASK_PID_DIR'):
        os.environ['GUNIFLASK_PID_DIR'] = join(home_dir, '.pid')


project_name_regex = re.compile(r'[a-zA-Z\-]+')


def infer_project_name(home_dir):
    init_file = join(home_dir, '.guniflask-init.json')
    if isfile(init_file):
        try:
            with open(init_file, 'r') as f:
                data = json.load(f)
            project_name = data.get('project_name')
            if project_name and isdir(join(home_dir, project_name)):
                return project_name
        except Exception:
            pass
    candidates = []
    for d in os.listdir(home_dir):
        if project_name_regex.fullmatch(d) and isfile(join(home_dir, d, '__init__.py')) \
                and isfile(join(home_dir, d, 'app.py')):
            candidates.append(d)
    if len(candidates) == 0:
        return None
    if len(candidates) > 1:
        raise RuntimeError('Cannot infer the project name, candidates: {}'.format(candidates))
    return candidates[0]


def get_project_name_from_env():
    return os.environ.get('GUNIFLASK_PROJECT_NAME')
